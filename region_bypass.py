from mitmproxy import http
import json
import os
import base64
import re
from console import Console
from config import TARGET_REGION, ALL_GAME_DOMAINS
from protobuf_patcher import process_majorlogin_request, process_getlogindata_request
from encryption_utils import aes_decrypt
from protobuf_utils import get_available_room
from database import check_uid, inc_stat, log_login, lookup_geo


def _decode_jwt(token):
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        # Free Fire lưu UID ở trường account_id hoặc uid
        if "account_id" in payload:
            return str(payload["account_id"])
        if "uid" in payload:
            return str(payload["uid"])
    except Exception:
        pass
    return None


def _extract_uid_from_flow(flow):
    # 1. Thử tìm JWT trong Header (Dành cho các request sau khi đã login)
    auth = flow.request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        uid = _decode_jwt(auth[7:])
        if uid:
            return uid

    # 2. Tìm JWT trong phần Response của Server (Dành cho request MajorLogin)
    if flow.response and flow.response.content:
        try:
            # Quét chuỗi văn bản để tìm JWT (thường bắt đầu bằng eyJ...)
            text = flow.response.content.decode('utf-8', errors='ignore')
            match = re.search(r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', text)
            if match:
                uid = _decode_jwt(match.group(0))
                if uid:
                    return uid
        except Exception:
            pass
            
    return None


class RegionBypass:
    def __init__(self):
        Console.info("Region Bypass initialized", target_region=TARGET_REGION)

    def _is_game_domain(self, host):
        return any(d in host for d in ALL_GAME_DOMAINS)

    def request(self, flow: http.HTTPFlow):
        host = flow.request.host
        if not self._is_game_domain(host):
            return

        # =====================================================================
        # CHỐT CHẶN 1: KIỂM TRA UID NGAY KHI REQUEST VỪA ĐƯỢC GỬI ĐI
        # (Fix lỗi đổi acc liên tục mà lọt qua nhờ cache)
        # =====================================================================
        uid_from_header = _extract_uid_from_flow(flow)
        if uid_from_header:
            sub = check_uid(uid_from_header)
            if not sub["valid"]:
                Console.error(f"CHẶN TỪ REQUEST - UID {uid_from_header} không hợp lệ!")
                
                # Cấu hình text và màu sắc chặn trên Game
                msg = (
                    "[FFFFFF]BYPASS CODE 400 FF MAX IND BY @hungheo88\n"
                    f"[808080]UID : [FFFFFF]{uid_from_header}\n"
                    "[808080]STATUS : [FF0000]ACCESS HAS EXPIRED[FFFFFF] , PLEASE CONTACT "
                    "[0000FF]TELEGRAM : @hungheo88[FFFFFF] TO BE GRANTED PERMISSION."
                )
                flow.response = http.Response.make(400, msg.encode(), {"Content-Type": "text/plain"})
                return

        if not flow.request.content:
            return

        raw = flow.request.content
        if len(raw) < 32:
            return

        try:
            dec = aes_decrypt(raw.hex())
            if not dec or len(dec) <= 10:
                return
            proto_json = get_available_room(dec.hex())
            if not proto_json:
                return
            proto = json.loads(proto_json)
            if "7" not in proto or proto["7"].get("wire_type") != "string":
                return

            path = flow.request.path
            if "/MajorLogin" in path:
                new_hex = process_majorlogin_request(raw.hex(), TARGET_REGION)
                if new_hex and new_hex != raw.hex():
                    flow.request.content = bytes.fromhex(new_hex)
                    flow.request.headers["Content-Length"] = str(len(flow.request.content))
                    Console.success(f"MajorLogin patched", field7=proto["7"]["data"])
            elif "/GetLoginData" in path:
                new_hex = process_getlogindata_request(raw.hex(), TARGET_REGION)
                if new_hex and new_hex != raw.hex():
                    flow.request.content = bytes.fromhex(new_hex)
                    flow.request.headers["Content-Length"] = str(len(flow.request.content))
                    Console.success(f"GetLoginData patched", field7=proto["7"]["data"])
        except Exception as e:
            Console.error(f"Patch error: {host}{flow.request.path}: {e}")

    def response(self, flow: http.HTTPFlow):
        if not flow.response:
            return
        host = flow.request.host
        path = flow.request.path

        if not self._is_game_domain(host):
            return
        if flow.request.method.upper() != "POST" or "/MajorLogin" not in path:
            return

        # Đọc thông tin IP
        client_ip = None
        try:
            client_ip = flow.client_conn.peername[0]
        except Exception:
            pass
        country, region_name, city = lookup_geo(client_ip)

        # =====================================================================
        # CHỐT CHẶN 2: KIỂM TRA UID TỪ RESPONSE (Dành cho lúc mới đăng nhập)
        # =====================================================================
        uid = _extract_uid_from_flow(flow)

        if not uid:
            inc_stat("blocked")
            log_login("UNKNOWN", client_ip, country, region_name, city, "BLOCKED (no_uid)")
            Console.error(f"UID : UNKNOWN - Can't Login (Không thể đọc UID từ Server)")
            self._send_notification("UNKNOWN", "BLOCKED", client_ip, country, city, "no_uid")

            msg = (
                "[FFFFFF]BYPASS CODE 400 FF MAX IND BY @hungheo88\n"
                "[808080]UID : [FFFFFF]UNKNOWN\n"
                "[808080]STATUS : [FF0000]ACCESS HAS EXPIRED[FFFFFF] , PLEASE CONTACT "
                "[0000FF]TELEGRAM : @hungheo88[FFFFFF] TO BE GRANTED PERMISSION."
            )
            flow.response.content = msg.encode()
            flow.response.status_code = 400
            return

        inc_stat("total")
        sub = check_uid(uid)
        
        if not sub["valid"]:
            inc_stat("blocked")
            log_login(uid, client_ip, country, region_name, city, f"BLOCKED ({sub['reason']})")
            
            Console.error(f"UID : {uid} Can't Login - Reason: {sub['reason']}")
            self._send_notification(uid, "BLOCKED", client_ip, country, city, sub["reason"])

            # HIỂN THỊ UID VÀ MÀU SẮC LÊN MÀN HÌNH GAME (KHI LỖI)
            msg = (
                "[FFFFFF]BYPASS CODE 400 FF MAX IND BY @hungheo88\n"
                f"[808080]UID : [FFFFFF]{uid}\n"
                "[808080]STATUS : [FF0000]ACCESS HAS EXPIRED[FFFFFF] , PLEASE CONTACT "
                "[0000FF]TELEGRAM : @hungheo88[FFFFFF] TO BE GRANTED PERMISSION."
            )
            flow.response.content = msg.encode()
            flow.response.status_code = 400
        else:
            inc_stat("allowed")
            log_login(uid, client_ip, country, region_name, city, f"ALLOWED ({sub['reason']})")
            
            # IN THÔNG BÁO THÀNH CÔNG LÊN CONSOLE PC (Không chèn vào Game để tránh lỗi Lobby)
            Console.success(f"BYPASS CODE 400 FF MAX IND BY @hungheo88")
            Console.success(f"UID : {uid}")
            Console.success(f"STATUS : VERIFICATION SUCCESSFUL, NOW PLAY GAME !")
            
            self._send_notification(uid, "ALLOWED", client_ip, country, city, sub["reason"])

    def _send_notification(self, uid, status, ip, country, city, reason=""):
        try:
            from discord_notify import send_discord_notification
            send_discord_notification(uid, status, ip, country, city, reason)
        except Exception:
            pass


addons = [RegionBypass()]