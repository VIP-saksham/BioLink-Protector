"""
Author: Elite Sid + Modified with Log & Broadcast
"""

import time
import re
import importlib
from pyrogram import Client, filters, errors
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

from helper.utils import (
    is_admin,
    get_config, update_config,
    increment_warning, reset_warnings,
    is_whitelisted, add_whitelist, remove_whitelist, get_whitelist
)

from config import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    URL_PATTERN,
    OWNER_ID,
    LOG_CHANNEL
)

# ---------------- BOT INIT ---------------- #
app = Client(
    "biolink_protector_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
)

# ---------------- LOG FUNCTION ---------------- #
async def send_log(client, text):
    try:
        await client.send_message(LOG_CHANNEL, text, disable_web_page_preview=True)
    except Exception as e:
        print(f"Log Error: {e}")

# ---------------- START ---------------- #
@app.on_message(filters.command("start"))
async def start_handler(client: Client, message):
    chat_id = message.chat.id
    bot = await client.get_me()
    add_url = f"https://t.me/{bot.username}?startgroup=true"
    text = (
        "**✨ Welcome to BioLink Protector Bot! ✨**\n\n"
        "🛡️ I help protect your groups from users with links in their bio.\n\n"
        "Use /help to see all available commands."
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Me to Your Group", url=add_url)],
        [InlineKeyboardButton("🛠️ Support", url="https://t.me/TeamsXchat"),
         InlineKeyboardButton("🗑️ Close", callback_data="close")]
    ])
    await client.send_message(chat_id, text, reply_markup=kb)

# ---------------- HELP ---------------- #
@app.on_message(filters.command("help"))
async def help_handler(client: Client, message):
    help_text = (
        "**🛠️ Bot Commands & Usage**\n\n"
        "`/config` – set warn-limit & punishment mode\n"
        "`/free` – whitelist a user (reply or user/id)\n"
        "`/unfree` – remove from whitelist\n"
        "`/freelist` – list all whitelisted users\n"
        "`/broadcast` – send msg to all groups (Owner only)\n"
        "`/ping` – check bot latency"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🗑️ Close", callback_data="close")]])
    await client.send_message(message.chat.id, help_text, reply_markup=kb)

# ---------------- PING ---------------- #
@app.on_message(filters.command("ping"))
async def ping_handler(client: Client, message):
    start = time.time()
    reply = await message.reply("🏓 Pinging...")
    end = time.time()
    ping_time = round((end - start) * 1000)
    await reply.edit_text(f"🏓 Pong!\n⏱️ `{ping_time}ms`")

# ---------------- BROADCAST ---------------- #
@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client: Client, message):
    if message.from_user.id != OWNER_ID:
        return await message.reply("❌ You are not authorized.")

    if not message.reply_to_message:
        return await message.reply("Reply to a message to broadcast.")

    groups = await get_all_groups()  # helper se group ids nikale
    success, fail = 0, 0
    for chat_id in groups:
        try:
            await message.reply_to_message.copy(chat_id)
            success += 1
        except Exception:
            fail += 1

    await message.reply(f"✅ Broadcast Done\nSuccess: {success}\nFailed: {fail}")

# ---------------- BIO CHECK ---------------- #
@app.on_message(filters.group)
async def check_bio(client: Client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if await is_admin(client, chat_id, user_id) or await is_whitelisted(chat_id, user_id):
        return

    user = await client.get_chat(user_id)
    bio = user.bio or ""
    full_name = f"{user.first_name}{(' ' + user.last_name) if user.last_name else ''}"
    mention = f"[{full_name}](tg://user?id={user_id})"

    if URL_PATTERN.search(bio):
        try:
            await message.delete()
        except errors.MessageDeleteForbidden:
            return await message.reply_text("Please grant me delete permission.")

        mode, limit, penalty = await get_config(chat_id)
        count = await increment_warning(chat_id, user_id)

        warning_text = (
            "🚨 **Warning Issued** 🚨\n\n"
            f"👤 **User:** {mention} `[{user_id}]`\n"
            "❌ **Reason:** URL found in bio\n"
            f"⚠️ **Warning:** {count}/{limit}\n"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel Warning", callback_data=f"cancel_warn_{user_id}"),
             InlineKeyboardButton("✅ Whitelist", callback_data=f"whitelist_{user_id}")],
            [InlineKeyboardButton("🗑️ Close", callback_data="close")]
        ])
        sent = await message.reply_text(warning_text, reply_markup=keyboard)

        # --- LOG ACTION --- #
        await send_log(client,
            f"📢 **BioLink Alert**\n\n"
            f"👥 Chat: `{chat_id}`\n"
            f"👤 User: {mention} (`{user_id}`)\n"
            f"⚠️ Warning: {count}/{limit}\n"
            f"⚡ Action: Message Deleted"
        )

        if count >= limit:
            try:
                if penalty == "mute":
                    await client.restrict_chat_member(chat_id, user_id, ChatPermissions())
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unmute ✅", callback_data=f"unmute_{user_id}")]])
                    await sent.edit_text(f"**{mention} has been 🔇 muted.**", reply_markup=kb)
                    await send_log(client, f"🔇 **Muted:** {mention} (`{user_id}`) in `{chat_id}`")
                else:
                    await client.ban_chat_member(chat_id, user_id)
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Unban ✅", callback_data=f"unban_{user_id}")]])
                    await sent.edit_text(f"**{mention} has been 🔨 banned.**", reply_markup=kb)
                    await send_log(client, f"🔨 **Banned:** {mention} (`{user_id}`) in `{chat_id}`")
            except errors.ChatAdminRequired:
                await sent.edit_text(f"**I don't have permission to {penalty} users.**")

    else:
        await reset_warnings(chat_id, user_id)

# ---------------- GROUP LIST HELPER ---------------- #
async def get_all_groups():
    groups = await punishments_collection.distinct("chat_id")
    return groups

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    app.run()
