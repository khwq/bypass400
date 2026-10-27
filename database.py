import sqlite3
import time
import os
import requests
import re

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_data.db")

_conn = sqlite3.connect(DB_FILE, check_same_thread=False)
_cur = _conn.cursor()

_cur.execute("CREATE TABLE IF NOT EXISTS whitelist (uid TEXT PRIMARY KEY, region TEXT DEFAULT 'GLOBAL', expires_at INTEGER DEFAULT 0)")
_cur.execute("CREATE TABLE IF NOT EXISTS blacklist (uid TEXT PRIMARY KEY)")
_cur.execute("""
CREATE TABLE IF NOT EXISTS login_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid TEXT, ip TEXT, country TEXT, region TEXT, city TEXT, ts INTEGER, status TEXT
)""")
_cur.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER)")
_conn.commit()

for k in ("total", "allowed", "blocked"):
    _cur.execute("INSERT OR IGNORE INTO stats (key, value) VALUES (?, ?)", (k, 0))
_conn.commit()


def inc_stat(name):
    _cur.execute("UPDATE stats SET value = value + 1 WHERE key=?", (name,))
    _conn.commit()


def get_stats():
    _cur.execute("SELECT count(*) as c FROM whitelist")
    wl = _cur.fetchone()[0]
    _cur.execute("SELECT count(*) as c FROM blacklist")
    bl = _cur.fetchone()[0]
    _cur.execute("SELECT key, value FROM stats")
    st = {r[0]: r[1] for r in _cur.fetchall()}
    return {"whitelist_count": wl, "blacklist_count": bl, "stats": st}


def log_login(uid, ip, country, region, city, status):
    ts = int(time.time())
    _cur.execute("INSERT INTO login_logs (uid, ip, country, region, city, ts, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (uid, ip, country, region, city, ts, status))
    _conn.commit()


def add_uid(uid, region="GLOBAL", duration="lifetime"):
    expires_at = 0
    if duration != "lifetime":
        try:
            hours = int(duration)
            if hours > 0:
                expires_at = int(time.time()) + (hours * 3600)
        except ValueError:
            pass
    _cur.execute("INSERT OR REPLACE INTO whitelist (uid, region, expires_at) VALUES (?, ?, ?)",
                 (uid, region, expires_at))
    _conn.commit()


def remove_uid(uid):
    _cur.execute("DELETE FROM whitelist WHERE uid=?", (uid,))
    _conn.commit()


def get_all_uids():
    _cur.execute("SELECT uid, region, expires_at FROM whitelist")
    return [{"uid": r[0], "region": r[1], "expires_at": r[2]} for r in _cur.fetchall()]


def check_uid(uid):
    uid = str(uid).strip()

    _cur.execute("SELECT 1 FROM blacklist WHERE uid=?", (uid,))
    if _cur.fetchone():
        return {"valid": False, "reason": "blacklisted"}

    try:
        _cur.execute("SELECT region, expires_at FROM whitelist WHERE uid=?", (uid,))
        row = _cur.fetchone()
        if row:
            region, expires_at = row
            if expires_at and expires_at > 0:
                if int(time.time()) > expires_at:
                    return {"valid": False, "reason": "expired"}
            return {"valid": True, "reason": "whitelisted"}
    except sqlite3.OperationalError:
        pass

    return {"valid": False, "reason": "not_whitelisted"}


def lookup_geo(ip):
    if not ip or ip == "127.0.0.1":
        return "Local", "Local", "Local"
    try:
        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=5,
                         proxies={"http": None, "https": None})
        j = r.json()
        return j.get("country", "Unknown"), j.get("regionName", "Unknown"), j.get("city", "Unknown")
    except Exception:
        return "Unknown", "Unknown", "Unknown"
