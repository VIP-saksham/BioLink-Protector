# helper/utils.py
# Database + Command Handlers for BioLink Protector Bot
# ======================================================

from config import MONGO_DB_URI, API_ID, API_HASH, BOT_TOKEN, DEFAULT_CONFIG, URL_PATTERN
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters, enums
from pyrogram.types import ChatPermissions
import time

# ==========================
# 📌 MongoDB connection
# ==========================
mongo = AsyncIOMotorClient(MONGO_DB_URI)
db = mongo["biolink_protector"]

# Collections
warnings_collection = db["warnings"]
punishments_collection = db["punishments"]
whitelist_collection = db["whitelist"]
config_collection = db["config"]

# ==========================
# 📌 Admin Check
# ==========================
async def is_admin(client: Client, chat_id: int, user_id: int) -> bool:
    async for member in client.get_chat_members(
        chat_id,
        filter=enums.ChatMembersFilter.ADMINISTRATORS
    ):
        if member.user.id == user_id:
            return True
    return False

# ==========================
# 📌 Config Functions
# ==========================
async def get_config(chat_id: int):
    doc = await config_collection.find_one({'chat_id': chat_id})
    if doc:
        return {
            "mode": doc.get('mode', DEFAULT_CONFIG["mode"]),
            "limit": doc.get('limit', DEFAULT_CONFIG["limit"]),
            "penalty": doc.get('penalty', DEFAULT_CONFIG["penalty"]),
            "anti_link": doc.get('anti_link', DEFAULT_CONFIG["anti_link"]),
        }
    return DEFAULT_CONFIG.copy()

async def update_config(chat_id: int, mode=None, limit=None, penalty=None, anti_link=None):
    update = {}
    if mode is not None:
        update['mode'] = mode
    if limit is not None:
        update['limit'] = limit
    if penalty is not None:
        update['penalty'] = penalty
    if anti_link is not None:
        update['anti_link'] = anti_link
    if update:
        await config_collection.update_one(
            {'chat_id': chat_id},
            {'$set': update},
            upsert=True
        )

# ==========================
# 📌 Warning System
# ==========================
async def increment_warning(chat_id: int, user_id: int) -> int:
    await warnings_collection.update_one(
        {'chat_id': chat_id, 'user_id': user_id},
        {'$inc': {'count': 1}},
        upsert=True
    )
    doc = await warnings_collection.find_one({'chat_id': chat_id, 'user_id': user_id})
    return doc['count']

async def reset_warnings(chat_id: int, user_id: int):
    await warnings_collection.delete_one({'chat_id': chat_id, 'user_id': user_id})

# ==========================
# 📌 Whitelist System
# ==========================
async def is_whitelisted(chat_id: int, user_id: int) -> bool:
    doc = await whitelist_collection.find_one({'chat_id': chat_id, 'user_id': user_id})
    return bool(doc)

async def add_whitelist(chat_id: int, user_id: int):
    await whitelist_collection.update_one(
        {'chat_id': chat_id, 'user_id': user_id},
        {'$set': {'user_id': user_id}},
        upsert=True
    )

async def remove_whitelist(chat_id: int, user_id: int):
    await whitelist_collection.delete_one({'chat_id': chat_id, 'user_id': user_id})

async def get_whitelist(chat_id: int) -> list:
    cursor = whitelist_collection.find({'chat_id': chat_id})
    docs = await cursor.to_list(length=None)
    return [doc['user_id'] for doc in docs]

# ==========================
# 📌 Broadcast Helper
# ==========================
async def get_all_groups():
    groups = await punishments_collection.distinct("chat_id")
    return groups

# ==========================
# 📌 Bot Client
# ==========================
app = Client(
    "biolink_protector_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# ==========================
# 📌 Anti-Link Protection
# ==========================
@app.on_message(filters.group & filters.text)
async def anti_link_filter(client, message):
    chat_id = message.chat.id
    config = await get_config(chat_id)

    if config["anti_link"]:
        if URL_PATTERN.search(message.text):
            if not await is_admin(client, chat_id, message.from_user.id):
                await message.delete()
                await message.reply_text(f"🚫 {message.from_user.mention}, links allowed nahi hai yaha!")

# ==========================
# 📌 Bio Check on Join
# ==========================
@app.on_message(filters.new_chat_members)
async def bio_check(client, message):
    chat_id = message.chat.id
    config = await get_config(chat_id)

    for user in message.new_chat_members:
        # Ignore admins
        if await is_admin(client, chat_id, user.id):
            continue
        # Ignore whitelist
        if await is_whitelisted(chat_id, user.id):
            continue

        bio_text = (user.bio or "") + " " + (user.username or "")
        if URL_PATTERN.search(bio_text):
            count = await increment_warning(chat_id, user.id)

            if count >= config["limit"]:
                if config["penalty"] == "mute":
                    await client.restrict_chat_member(chat_id, user.id, ChatPermissions())
                    await message.reply_text(f"🔇 {user.mention} ko mute kar diya gaya (bio me link hone ki wajah se).")
                elif config["penalty"] == "ban":
                    await client.ban_chat_member(chat_id, user.id)
                    await message.reply_text(f"🔨 {user.mention} ko ban kar diya gaya (bio me link hone ki wajah se).")
                await reset_warnings(chat_id, user.id)
            else:
                await message.reply_text(
                    f"⚠️ {user.mention} ke bio/username me link detect hua.\nWarning {count}/{config['limit']}"
                )

# ==========================
# 📌 Ping Command
# ==========================
@app.on_message(filters.command("ping"))
async def ping(client, message):
    start = time.time()
    reply = await message.reply_text("🏓 Pinging...")
    end = time.time()
    ms = (end - start) * 1000
    await reply.edit_text(f"🏓 Pong!\n⏱️ {int(ms)}ms")

# ==========================
# 📌 Run App
# ==========================
if __name__ == "__main__":
    app.run()
