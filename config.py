# Copyright (C) @SID_ELITE
# Channel: https://t.me/TeamXUpdate

import re

API_ID = "12345678" # Your Telegram API ID
API_HASH = "12345678abcd" # Your Telegram API Hash
BOT_TOKEN = "7267436522:XXXXXXXXXXXXXXXXXX" # Your Bot Token

# MongoDB connection URI
MONGO_URI = "your_mongodb_url"

DEFAULT_WARNING_LIMIT = 3
DEFAULT_PUNISHMENT = "mute" # Options: "mute", "ban"
DEFAULT_CONFIG = ("warn", DEFAULT_WARNING_LIMIT, DEFAULT_PUNISHMENT)

# Regex pattern to detect URLs in user bios
URL_PATTERN = re.compile(
    r'(https?://|www\.)[a-zA-Z0-9.\-]+(\.[a-zA-Z]{2,})+(/[a-zA-Z0-9._%+-]*)*' #done change here
)
