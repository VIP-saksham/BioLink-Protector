# helper/utils.py
# Database + Command Handlers for BioLink Protector Bot
# ======================================================

from config import MONGO_DB_URI, API_ID, API_HASH, BOT_TOKEN
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters, enums
from pyrogram.types import ChatPermissions
import re
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
DEFAULT_CONFIG = ("warn", 3, "mute")  # mode, limit, penalty

async def get_config(chat_id: int):
    doc = await config_collection.find_one({'chat_id': chat_id})
    if doc:
        return (
            doc.get('mode', 'warn'),
            doc.get('limit', DEFAULT_CONFIG[1]),
            doc.get('penalty', DEFAULT_CONFIG[2])
        )
    return DEFAULT_CONFIG


async def update_config(chat_id: int, mode=None, limit=None, penalty=None):
    update = {}
    if mode is not None:
        update['mode'] = mode
    if limit is not None:
        update['limit'] = limit
    if penalty is not None:
        update['penalty'] = penalty
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
    """Sabhi groups ke chat_id return karega (broadcast ke liye)"""
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
# 📌 Commands
# ==========================

# /warn
@app.on_message(filters.command("warn") & filters.group)
async def warn_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        return await message.reply_text("❌ Sirf admin hi warn kar sakte hain.")

    if not message.reply_to_message:
        return await message.reply_text("⚠️ Kisi user ko reply karke `/warn` use karo.")

    target = message.reply_to_message.from_user

    # Agar user whitelist me hai
    if await is_whitelisted(chat_id, target.id):
        return await message.reply_text("✅ Ye user whitelist me hai.")

    # Warnings increase
    count = await increment_warning(chat_id, target.id)
    mode, limit, penalty = await get_config(chat_id)

    if count >= limit:
        # Punish user
        if penalty == "mute":
            await client.restrict_chat_member(chat_id, target.id, ChatPermissions())
            await message.reply_text(f"🔇 {target.mention} ko mute kar diya gaya. [Limit cross]")
        elif penalty == "ban":
            await client.ban_chat_member(chat_id, target.id)
            await message.reply_text(f"🔨 {target.mention} ko ban kar diya gaya. [Limit cross]")

        await reset_warnings(chat_id, target.id)
    else:
        await message.reply_text(
            f"⚠️ {target.mention} ko warning mili hai.\nWarnings: {count}/{limit}"
        )


# /whitelist
@app.on_message(filters.command("whitelist") & filters.group)
async def whitelist_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        return

    if not message.reply_to_message:
        return await message.reply_text("⚠️ Kisi user ko reply karke `/whitelist` karo.")

    target = message.reply_to_message.from_user
    await add_whitelist(chat_id, target.id)
    await reset_warnings(chat_id, target.id)

    await message.reply_text(f"✅ {target.mention} whitelist me add kar diya gaya.")


# /unwhitelist
@app.on_message(filters.command("unwhitelist") & filters.group)
async def unwhitelist_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not await is_admin(client, chat_id, user_id):
        return

    if not message.reply_to_message:
        return await message.reply_text("⚠️ Kisi user ko reply karke `/unwhitelist` karo.")

    target = message.reply_to_message.from_user
    await remove_whitelist(chat_id, target.id)

    await message.reply_text(f"🚫 {target.mention} ko whitelist se hata diya gaya.")


# /freelist
@app.on_message(filters.command("freelist") & filters.group)
async def show_whitelist(client, message):
    chat_id = message.chat.id
    ids = await get_whitelist(chat_id)

    if not ids:
        return await message.reply_text("⚠️ Whitelist me koi nahi hai.")

    text = "**📋 Whitelisted Users:**\n\n"
    for i, uid in enumerate(ids, start=1):
        try:
            user = await client.get_users(uid)
            text += f"{i}. {user.mention} (`{uid}`)\n"
        except:
            text += f"{i}. `{uid}` (User not found)\n"

    await message.reply_text(text)


# /broadcast (owner only)
@app.on_message(filters.command("broadcast") & filters.user([123456789]))  # owner id daalna
async def broadcast_message(client, message):
    if len(message.command) < 2:
        return await message.reply_text("⚠️ Usage: `/broadcast your_message`")

    text = " ".join(message.command[1:])
    groups = await get_all_groups()

    for chat_id in groups:
        try:
            await client.send_message(chat_id, f"📢 **Broadcast:** {text}")
        except Exception as e:
            print(f"❌ Failed in {chat_id}: {e}")

    await message.reply_text("✅ Broadcast complete.")


# /ping
@app.on_message(filters.command("ping"))
async def ping(client, message):
    start = time.time()
    reply = await message.reply_text("🏓 Pinging...")
    end = time.time()
    ms = (end - start) * 1000
    await reply.edit_text(f"🏓 Pong!\n⏱️ {int(ms)}ms")


from pyrogram.errors import RPCError
import re

# ==========================
# 📌 Anti-Link System
# ==========================
@app.on_message(filters.text & filters.group, group=5)  # group=5 taaki priority last me ho
async def anti_link(client, message):
    chat_id = message.chat.id
    user = message.from_user

    if not user:  # system message ignore
        return

    text = message.text or message.caption or ""

    # Agar message me link hai
    if re.search(r"(https?://|t\.me/|telegram\.me/)", text, re.IGNORECASE):
        # Admin aur whitelist exempt
        if await is_admin(client, chat_id, user.id):
            return
        if await is_whitelisted(chat_id, user.id):
            return

        try:
            await message.delete()
            await message.reply_text(
                f"❌ {user.mention}, group me links allowed nahi hai.",
                quote=True
            )
        except RPCError as e:
            print(f"AntiLink Error: {e}")

# ==========================
# 📌 Run App
# ==========================
if __name__ == "__main__":
    app.run()
