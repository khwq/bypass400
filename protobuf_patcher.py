import json
from encryption_utils import aes_decrypt, encrypt_api
from protobuf_utils import get_available_room, CrEaTe_ProTo

TARGET_VERSION_MIDDLE = "132"
TARGET_VERSION_CODE = "2019118525"

def decode_proto(hex_data):
    try:
        dec = aes_decrypt(hex_data)
        proto_json = get_available_room(dec.hex())
        if proto_json:
            return json.loads(proto_json)
    except Exception as e:
        print(f"[Proto] Decode error: {e}")
    return None

def encode_proto(proto_dict):
    try:
        proto_bytes = CrEaTe_ProTo(proto_dict)
        return encrypt_api(proto_bytes)
    except Exception as e:
        print(f"[Proto] Encode error: {e}")
    return None

def process_majorlogin_request(hex_data, target_region="IND"):
    """MajorLogin: patch field 7 (version) ONLY."""
    proto = decode_proto(hex_data)
    if not proto:
        return hex_data

    patched = json.loads(json.dumps(proto))

    if "7" in patched and patched["7"].get("wire_type") == "string":
        old_ver = patched["7"]["data"]
        parts = old_ver.split('.')
        if len(parts) == 3 and parts[1] != TARGET_VERSION_MIDDLE:
            parts[1] = TARGET_VERSION_MIDDLE
            new_ver = '.'.join(parts)
            patched["7"]["data"] = new_ver
            print(f"[MajorLogin] Field 7: {old_ver} -> {new_ver}")

    new_hex = encode_proto(patched)
    return new_hex if new_hex else hex_data

def process_getlogindata_request(hex_data, target_region="IND"):
    """GetLoginData: patch field 83 (versionCode) ONLY."""
    proto = decode_proto(hex_data)
    if not proto:
        return hex_data

    patched = json.loads(json.dumps(proto))

    if "83" in patched and patched["83"].get("wire_type") == "string":
        old_vc = patched["83"]["data"]
        if old_vc != TARGET_VERSION_CODE:
            patched["83"]["data"] = TARGET_VERSION_CODE
            print(f"[GetLoginData] Field 83: {old_vc} -> {TARGET_VERSION_CODE}")

    new_hex = encode_proto(patched)
    return new_hex if new_hex else hex_data
