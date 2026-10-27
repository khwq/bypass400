from console import Console
import subprocess
import sys
import os
import time
import glob
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOCAL_BIN = os.path.join(BASE_DIR, ".local", "bin")
LOCAL_LIB = os.path.join(BASE_DIR, ".local", "lib")
if os.path.isdir(LOCAL_BIN):
    os.environ["PATH"] = LOCAL_BIN + os.pathsep + os.environ.get("PATH", "")
if os.path.isdir(LOCAL_LIB):
    for p in glob.glob(os.path.join(LOCAL_LIB, "python*", "site-packages")):
        if p not in sys.path:
            sys.path.insert(0, p)


def is_port_in_use(port):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def find_mitmdump():
    import shutil
    path = shutil.which("mitmdump")
    if path:
        return path
    local = os.path.join(BASE_DIR, ".local", "bin", "mitmdump")
    if os.path.isfile(local):
        return local
    return None


if __name__ == "__main__":
    if sys.platform == "win32":
        os.system("")

    proxy_port = os.environ.get("SERVER_PORT", "8080")

    Console.success("Region Bypass - Starting Services")
    Console.info(f"Proxy port: {proxy_port}")

    # Start Discord Bot in background thread
    try:
        from discord_bot import start_bot
        bot_thread = threading.Thread(target=start_bot, daemon=True)
        bot_thread.start()
        Console.success("Discord Bot started")
    except Exception as e:
        Console.error(f"Failed to start Discord Bot: {e}")

    mitmdump_path = find_mitmdump()

    if mitmdump_path:
        mitm_args = [
            mitmdump_path,
            "-s", os.path.join(BASE_DIR, "region_bypass.py"),
            "--listen-host", "0.0.0.0",
            "-p", proxy_port,
            "--set", "block_global=false",
            "--set", "console_eventlog_verbosity=warn",
            "--set", "flow_detail=1",
        ]
    else:
        Console.info("mitmdump binary not found, using python -m approach")
        mitm_args = [
            sys.executable, "-m", "mitmproxy.tools.main", "mitmdump",
            "-s", os.path.join(BASE_DIR, "region_bypass.py"),
            "--listen-host", "0.0.0.0",
            "-p", proxy_port,
            "--set", "block_global=false",
            "--set", "console_eventlog_verbosity=warn",
            "--set", "flow_detail=1",
        ]

    try:
        subprocess.Popen(mitm_args, cwd=BASE_DIR)
        time.sleep(4)
        if is_port_in_use(int(proxy_port)):
            Console.success(f"mitmproxy running on port {proxy_port}")
        else:
            Console.warn("mitmproxy may not have started yet")
    except Exception as e:
        Console.error(f"Failed to start mitmproxy: {e}")

    Console.success(f"All services started. Proxy: 0.0.0.0:{proxy_port}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
