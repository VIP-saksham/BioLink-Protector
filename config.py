# ==========================================================
# 📌 BioLink Protector Bot Configuration
# ==========================================================

import re

# ==========================
# 🔑 API & BOT CONFIG
# ==========================
API_ID = 12345678  # ⚠️ Apna Telegram API ID daalo (int me rakho, string nahi)
API_HASH = "12345678abcd"  # ⚠️ Apna Telegram API Hash daalo
BOT_TOKEN = "7267436522:XXXXXXXXXXXXXXXXXX"  # ⚠️ Apna Bot Token daalo

# ==========================
# 📦 Database Config
# ==========================
MONGO_DB_URI = "your_mongodb_url"  # ⚠️ Apna MongoDB Connection URL daalo
DB_NAME = "biolink_protector"

# ==========================
# ⚙️ Default Settings
# ==========================
DEFAULT_WARNING_LIMIT = 3
DEFAULT_PUNISHMENT = "mute"   # Options: "mute", "ban"

# ⚠️ Default config (mode, limit, punishment, anti_link)
DEFAULT_CONFIG = {
    "mode": "warn",
    "limit": DEFAULT_WARNING_LIMIT,
    "penalty": DEFAULT_PUNISHMENT,
    "anti_link": True  # 🚫 Links by default block honge
}

# ==========================
# 🔗 Regex Patterns
# ==========================
# User bios ya messages me link detect karne ke liye
URL_PATTERN = re.compile(
    r"(https?://|www\.|t\.me/|telegram\.me/)[a-zA-Z0-9.\-]+(\.[a-zA-Z]{2,})*"
    r"(/[a-zA-Z0-9._%+-]*)*|@[\w_]+"
)
