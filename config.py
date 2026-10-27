import os

TARGET_REGION = "IND"
TARGET_COUNTRY_CODE = "IN"
TARGET_VERSION = "2.132.6"
TARGET_VERSION_CODE = "2019118525"

PATCH_MODE = "both"

OAUTH_DOMAINS = ["100067.connect.garena.com"]
LOGIN_DOMAINS = ["loginbp.ppmainecoonghj.com"]
CLIENT_DOMAINS = ["clientbp.ppmainecoonghj.com"]
ALL_GAME_DOMAINS = OAUTH_DOMAINS + LOGIN_DOMAINS + CLIENT_DOMAINS + [
    "dl.dir.freefiremobile.com",
    "sgevent.ggblueshark.com",
    "msdk.garena.com",
    "ff.garena.com",
    "garenanow.com",
]

# Đọc từ biến môi trường, nếu không có thì để trống
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_LOG_CHANNEL_ID = int(os.environ.get("DISCORD_LOG_CHANNEL_ID", "0"))
DISCORD_ADMIN_ROLE = "Bypass Admin"