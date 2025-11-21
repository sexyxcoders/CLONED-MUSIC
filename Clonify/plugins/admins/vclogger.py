# ===========================================================
# vclogger.py — Enhanced VC Logger for NexaMusic (WITH REFRESH)
# Features:
#  - /vclogger enable|disable|status|style|cooldown|delete_after|refresh
#  - /vcrefresh (admin-only)
#  - human-only logging, styles, cooldown, total count, join time
#  - inline "Show Full VC List" button (live)
#  - manual refresh: re-scan participants & restart monitor
# ===========================================================

import asyncio
import json
import random
import time
from datetime import datetime, timezone
from logging import getLogger
from typing import Dict, Set

from pyrogram import filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from pyrogram.raw import functions

from Clonify import app
#from Clonify.utils.database.assistant import get_assistant   # FIXED

LOGGER = getLogger(__name__)   # FIXED

# -------------------------
# Runtime state
# -------------------------
vc_active_users: Dict[int, Set[int]] = {}
active_vc_chats: Set[int] = set()
last_sent_time: Dict[int, float] = {}  # chat_id -> timestamp (cooldown)
recent_join_times: Dict[int, Dict[int, float]] = {}  # chat_id -> {user_id: join_ts}
_monitor_tasks: Dict[int, asyncio.Task] = {}  # chat_id -> task (optional handle)

# -------------------------
# Persistent config (JSON)
# -------------------------
CONFIG_FILE = "vclogger_config.json"
DEFAULT_COOLDOWN = 2  # seconds between alert messages per chat
DEFAULT_DELETE_AFTER = 10  # seconds before auto-delete of join/leave messages

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        LOGGER.error(f"[VCLOGGER] Failed to load config: {e}")
        return {}

def save_config(data):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        LOGGER.error(f"[VCLOGGER] Failed to save config: {e}")

_config = load_config()

def get_chat_cfg(chat_id):
    return _config.get(str(chat_id), {})

def set_chat_cfg(chat_id, key, value):
    cid = str(chat_id)
    if cid not in _config:
        _config[cid] = {}
    _config[cid][key] = value
    save_config(_config)

def is_enabled(chat_id):
    return bool(get_chat_cfg(chat_id).get("enabled", False))

def enable_logger(chat_id):
    set_chat_cfg(chat_id, "enabled", True)

def disable_logger(chat_id):
    cid = str(chat_id)
    if cid in _config:
        _config[cid]["enabled"] = False
        save_config(_config)

def get_cooldown(chat_id):
    return get_chat_cfg(chat_id).get("cooldown", DEFAULT_COOLDOWN)

def get_delete_after(chat_id):
    return get_chat_cfg(chat_id).get("delete_after", DEFAULT_DELETE_AFTER)

def get_style(chat_id):
    return get_chat_cfg(chat_id).get("style", "premium")  # default style

def set_style(chat_id, style_name):
    set_chat_cfg(chat_id, "style", style_name)

# -------------------------
# Styles (6 styles)
# Each returns (message_text, footer_emoji)
# -------------------------
def style_premium(name, username, user_id, total, join_time_iso):
    return (f"💫 <b>ɴᴇᴡ ᴍᴇᴍʙᴇʀ ᴇɴᴛᴇʀᴇᴅ ᴛʜᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ</b>\n\n"
            f"👤 <b>ᴘʀᴏғɪʟᴇ:</b> {name}\n"
            f"🔗 <b>ᴜsᴇʀɴᴀᴍᴇ:</b> {username}\n"
            f"🆔 <b>ɪᴅ:</b> <code>{user_id}</code>\n\n"
            f"👥 <b>Total in VC:</b> <code>{total}</code>\n"
            f"🕒 <i>Joined at: {join_time_iso}</i>\n\n"
            f"✨ <i>ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ᴠɪʙᴇs — ᴇɴᴊᴏʏ ᴛʜᴇ ᴠᴄ!</i>", "✨")

def style_neon(name, username, user_id, total, join_time_iso):
    return (f"💠 <b>ɴᴇᴏɴ ᴠᴄ ᴀʟᴇʀᴛ</b>\n\n"
            f"👤 <b>ɴᴀᴍᴇ:</b> {name}\n"
            f"🔗 <b>ᴜsᴇʀɴᴀᴍᴇ:</b> {username}\n"
            f"🆔 <b>ɪᴅ:</b> <code>{user_id}</code>\n\n"
            f"👥 <b>Total in VC:</b> <code>{total}</code>\n"
            f"🕒 <i>{join_time_iso}</i>\n\n"
            f"⚡ <i>ʏᴏᴜʀ ᴘʀᴇsᴇɴᴄᴇ ᴍᴀᴋᴇs ᴛʜᴇ ᴠᴄ ʟɪᴠᴇ!</i>", "⚡")

def style_royal(name, username, user_id, total, join_time_iso):
    return (f"👑 <b>ʀᴏʏᴀʟ ᴇɴᴛʀʏ ɪɴ ᴠᴄ</b>\n\n"
            f"✨ <b>ɴᴀᴍᴇ:</b> {name}\n"
            f"📛 <b>ᴜsᴇʀɴᴀᴍᴇ:</b> {username}\n"
            f"🆔 <b>ɪᴅ:</b> <code>{user_id}</code>\n\n"
            f"👥 <b>Total in VC:</b> <code>{total}</code>\n"
            f"🕒 <i>Joined: {join_time_iso}</i>\n\n"
            f"💛 <i>ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴛʜᴇ ɢᴏʟᴅᴇɴ ꜱᴜɴᴅ!</i>", "💛")

def style_anime(name, username, user_id, total, join_time_iso):
    return (f"🌸 <b>ᴀɴɪᴍᴇ ᴠᴄ ᴇɴᴛʀʏ</b>\n\n"
            f"👤 <b>ɴᴀᴍᴇ:</b> {name}\n"
            f"🌐 <b>ᴜsᴇʀɴᴀᴍᴇ:</b> {username}\n"
            f"🆔 <b>ɪᴅ:</b> <code>{user_id}</code>\n\n"
            f"👥 <b>Total in VC:</b> <code>{total}</code>\n"
            f"🕒 <i>{join_time_iso}</i>\n\n"
            f"💮 <i>ᴋᴏɴɴɪᴄʜɪᴡᴀ~ ᴇɴᴊᴏʏ ᴛʜᴇ ᴠᴄ!</i>", "💮")

def style_cyber(name, username, user_id, total, join_time_iso):
    return (f"🧬 <b>ᴄʏʙᴇʀ ᴍᴏᴅᴇ ᴀᴄᴛɪᴠᴀᴛᴇᴅ</b>\n\n"
            f"👤 <b>ᴜꜱᴇʀ:</b> {name}\n"
            f"📡 <b>ɴᴇᴛ ᴛᴀɢ:</b> {username}\n"
            f"🆔 <b>ᴄᴏᴅᴇ:</b> <code>{user_id}</code>\n\n"
            f"👥 <b>Total in VC:</b> <code>{total}</code>\n"
            f"🕒 <i>{join_time_iso}</i>\n\n"
            f"⚙️ <i>ᴜꜱᴇʀ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ ᴠᴄ ɴᴇᴛᴡᴏʀᴋ.</i>", "⚙️")

def style_dark(name, username, user_id, total, join_time_iso):
    return (f"🔥 <b>ᴅᴀʀᴋ ꜱᴏᴜʟ ᴇɴᴛᴇʀᴇᴅ ᴠᴄ</b>\n\n"
            f"😈 <b>ɴᴀᴍᴇ:</b> {name}\n"
            f"🔗 <b>ᴛᴀɢ:</b> {username}\n"
            f"🆔 <b>ɪᴅ:</b> <code>{user_id}</code>\n\n"
            f"👥 <b>Total in VC:</b> <code>{total}</code>\n"
            f"🕒 <i>{join_time_iso}</i>\n\n"
            f"🌑 <i>ᴛʜᴇ ᴠᴄ ɢᴏᴛ ᴅᴀʀᴋᴇʀ...</i>", "🌑")

_STYLE_FUNC = {
    "premium": style_premium,
    "neon": style_neon,
    "royal": style_royal,
    "anime": style_anime,
    "cyber": style_cyber,
    "dark": style_dark,
}

# -------------------------
# Helper — fetch participants (raw)
# -------------------------
async def get_group_call_participants(userbot, peer):
    try:
        full_chat = await userbot.invoke(functions.channels.GetFullChannel(channel=peer))
        if not hasattr(full_chat.full_chat, "call") or not full_chat.full_chat.call:
            return []
        call = full_chat.full_chat.call
        participants = await userbot.invoke(
            functions.phone.GetGroupParticipants(call=call, ids=[], sources=[], offset="", limit=100)
        )
        return participants.participants
    except Exception as e:
        error_msg = str(e).upper()
        if any(x in error_msg for x in ["GROUPCALL_NOT_FOUND", "CALL_NOT_FOUND", "NO_GROUPCALL"]):
            return []
        LOGGER.error(f"[VC LOGGER] Error fetching participants: {e}")
        return []

# -------------------------
# Cooldown guard
# -------------------------
def can_send_alert(chat_id):
    now = time.time()
    cd = get_cooldown(chat_id)
    last = last_sent_time.get(chat_id, 0)
    if now - last >= cd:
        last_sent_time[chat_id] = now
        return True
    return False

# -------------------------
# Monitor loop
# -------------------------
async def monitor_vc_chat(chat_id):
    userbot = await get_assistant(chat_id)
    if not userbot:
        return

    recent_join_times.setdefault(chat_id, {})

    try:
        while chat_id in active_vc_chats:
            try:
                peer = await userbot.resolve_peer(chat_id)
                participants_list = await get_group_call_participants(userbot, peer)

                new_users = {p.peer.user_id for p in participants_list if hasattr(p, "peer")}
                old_users = vc_active_users.get(chat_id, set())

                joined = new_users - old_users
                left = old_users - new_users

                # filter joins: only humans (not bots)
                human_joined = set()
                for uid in joined:
                    try:
                        usr = await userbot.get_users(uid)
                        if getattr(usr, "is_bot", False):
                            continue
                        if not uid:
                            continue
                        human_joined.add(uid)
                    except Exception:
                        continue

                tasks = []
                for uid in human_joined:
                    prev = recent_join_times[chat_id].get(uid, 0)
                    now_ts = time.time()
                    if now_ts - prev < 3:
                        continue
                    recent_join_times[chat_id][uid] = now_ts
                    tasks.append(handle_user_join(chat_id, uid, userbot))

                human_left = set()
                for uid in left:
                    try:
                        usr = await userbot.get_users(uid)
                        if getattr(usr, "is_bot", False):
                            continue
                        human_left.add(uid)
                    except Exception:
                        continue

                for uid in human_left:
                    tasks.append(handle_user_leave(chat_id, uid, userbot))

                if tasks:
                    if can_send_alert(chat_id):
                        await asyncio.gather(*tasks, return_exceptions=True)
                    else:
                        LOGGER.debug(f"[VCLOGGER] Cooldown active for {chat_id}, skipping immediate alerts.")

                vc_active_users[chat_id] = new_users

            except Exception as e:
                LOGGER.error(f"[VC LOGGER] Error in monitor loop for {chat_id}: {e}")

            await asyncio.sleep(2)
    finally:
        # cleanup on exit
        if chat_id in _monitor_tasks:
            _monitor_tasks.pop(chat_id, None)
        if chat_id in active_vc_chats:
            active_vc_chats.discard(chat_id)

# -------------------------
# Start monitor if needed
# -------------------------
async def check_and_monitor_vc(chat_id):
    userbot = await get_assistant(chat_id)
    if not userbot:
        return

    try:
        peer = await userbot.resolve_peer(chat_id)
        participants = await get_group_call_participants(userbot, peer)

        if participants and chat_id not in active_vc_chats and is_enabled(chat_id):
            active_vc_chats.add(chat_id)
            task = asyncio.create_task(monitor_vc_chat(chat_id))
            _monitor_tasks[chat_id] = task

    except Exception as e:
        LOGGER.error(f"[VC LOGGER] check_and_monitor error for {chat_id}: {e}")

# -------------------------
# Delete after delay helper
# -------------------------
async def delete_after_delay(msg, delay: int):
    try:
        await asyncio.sleep(delay)
        await msg.delete()
    except Exception:
        pass

# -------------------------
# Format time helper
# -------------------------
def iso_local_time():
    now = datetime.now(timezone.utc).astimezone()
    return now.strftime("%Y-%m-%d %H:%M:%S %Z")

# -------------------------
# Send join message (uses style)
# -------------------------
async def handle_user_join(chat_id, user_id, userbot):
    try:
        user = await userbot.get_users(user_id)
        name = (user.first_name or "ᴜɴᴋɴᴏᴡɴ").strip()
        username = f"@{user.username}" if getattr(user, "username", None) else "ɴᴏ ᴜsᴇʀɴᴀᴍᴇ"
        mention = f'<a href="tg://user?id={user_id}">{name}</a>'

        total = len(vc_active_users.get(chat_id, set())) + 1
        join_time_iso = iso_local_time()

        style = get_style(chat_id)
        if style == "random":
            style = random.choice(list(_STYLE_FUNC.keys()))
        style_func = _STYLE_FUNC.get(style, style_premium)
        text, footer = style_func(mention, username, user_id, total, join_time_iso)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Show Full VC List", callback_data=f"vclist:{chat_id}")],
            [InlineKeyboardButton("🔄 Refresh VC", callback_data=f"vcrefresh_cb:{chat_id}")],
            [InlineKeyboardButton("🔍 Profile", url=f"tg://user?id={user_id}")]
        ])

        sent = await app.send_message(chat_id, text, reply_markup=keyboard, disable_web_page_preview=True)
        asyncio.create_task(delete_after_delay(sent, get_delete_after(chat_id)))

    except Exception as e:
        LOGGER.error(f"[VC LOGGER] Join msg error for {user_id} in {chat_id}: {e}")

# -------------------------
# Send leave message
# -------------------------
async def handle_user_leave(chat_id, user_id, userbot):
    try:
        user = await userbot.get_users(user_id)
        name = (user.first_name or "ᴜɴᴋɴᴏᴡɴ").strip()
        username = f"@{user.username}" if getattr(user, "username", None) else "ɴᴏ ᴜsᴇʀɴᴀᴍᴇ"
        mention = f'<a href="tg://user?id={user_id}">{name}</a>'

        total = max(0, len(vc_active_users.get(chat_id, set())) - 1)
        leave_time_iso = iso_local_time()

        style = get_style(chat_id)
        if style == "random":
            style = random.choice(list(_STYLE_FUNC.keys()))
        style_func = _STYLE_FUNC.get(style, style_premium)
        text, footer = style_func(mention, username, user_id, total, leave_time_iso)
        text = text.replace("ɴᴇᴡ ᴍᴇᴍʙᴇʀ ᴇɴᴛᴇʀᴇᴅ ᴛʜᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ", "ᴍᴇᴍʙᴇʀ ʟᴇꜰᴛ ᴛʜᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ") \
                   .replace("ᴇɴᴛᴇʀᴇᴅ ᴛʜᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ", "ʟᴇꜰᴛ ᴛʜᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ") \
                   .replace("ɴᴇᴡ ᴍᴇᴍʙᴇʀ ᴊᴏɪɴᴇᴅ ᴠᴄ", "ᴍᴇᴍʙᴇʀ ʟᴇꜰᴛ ᴠᴄ")

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔍 Profile", url=f"tg://user?id={user_id}")]]
        )

        sent = await app.send_message(chat_id, text, reply_markup=keyboard, disable_web_page_preview=True)
        asyncio.create_task(delete_after_delay(sent, get_delete_after(chat_id)))

    except Exception as e:
        LOGGER.error(f"[VC LOGGER] Leave msg error for {user_id} in {chat_id}: {e}")

# -------------------------
# Utility: build members list text
# -------------------------
async def build_vc_members_text(chat_id):
    userbot = await get_assistant(chat_id)
    if not userbot:
        return "Assistant not available."

    try:
        peer = await userbot.resolve_peer(chat_id)
        participants = await get_group_call_participants(userbot, peer)
        lines = []
        for p in participants:
            if hasattr(p, "peer"):
                uid = p.peer.user_id
                try:
                    usr = await userbot.get_users(uid)
                    if getattr(usr, "is_bot", False):
                        continue
                    name = usr.first_name or "ᴜɴᴋɴᴏᴡɴ"
                    display = f"- {name}"
                    if getattr(usr, "username", None):
                        display += f" (@{usr.username})"
                    display += f" — <code>{uid}</code>"
                    lines.append(display)
                except Exception:
                    continue
        if not lines:
            return "No human participants found in VC."
        header = f"👥 <b>Current VC Members — {len(lines)}</b>\n\n"
        return header + "\n".join(lines)
    except Exception as e:
        LOGGER.error(f"[VCLOGGER] build_vc_members_text err: {e}")
        return "Failed to fetch VC participants."

# -------------------------
# Callback: show full VC list
# -------------------------
@app.on_callback_query(filters.regex(r"^vclist:"))
async def _vclist_cb(_, cb: CallbackQuery):
    try:
        await cb.answer()
        parts = (cb.data or "").split(":")
        if len(parts) != 2:
            return
        chat_id = int(parts[1])
        text = await build_vc_members_text(chat_id)
        # try to reply privately first
        try:
            await cb.message.reply_text(text, disable_web_page_preview=True)
        except Exception:
            await cb.edit_message_text(text, disable_web_page_preview=True)
    except Exception as e:
        LOGGER.error(f"[VCLOGGER] vclist cb err: {e}")

# -------------------------
# Callback: refresh VC (button)
# -------------------------
@app.on_callback_query(filters.regex(r"^vcrefresh_cb:"))
async def _vcrefresh_cb(_, cb: CallbackQuery):
    try:
        await cb.answer("Refreshing VC…", show_alert=False)
        parts = (cb.data or "").split(":")
        if len(parts) != 2:
            return
        chat_id = int(parts[1])
        # perform refresh
        await perform_vc_refresh(chat_id)
        # respond
        text = await build_vc_members_text(chat_id)
        await cb.message.reply_text("🔄 VC refreshed.\n\n" + text, disable_web_page_preview=True)
    except Exception as e:
        LOGGER.error(f"[VCLOGGER] vcrefresh cb err: {e}")

# -------------------------
# Manual refresh logic
# -------------------------
async def perform_vc_refresh(chat_id):
    """
    Force re-scan participants for chat_id, update vc_active_users,
    restart monitor if necessary. Returns set of current user ids.
    """
    userbot = await get_assistant(chat_id)
    if not userbot:
        return set()

    try:
        peer = await userbot.resolve_peer(chat_id)
        participants = await get_group_call_participants(userbot, peer)
        new_users = {p.peer.user_id for p in participants if hasattr(p, "peer")}
        # filter humans
        humans = set()
        for uid in new_users:
            try:
                usr = await userbot.get_users(uid)
                if getattr(usr, "is_bot", False):
                    continue
                humans.add(uid)
            except Exception:
                continue
        # update internal state
        vc_active_users[chat_id] = humans
        # restart monitor if enabled but not running
        if is_enabled(chat_id) and chat_id not in active_vc_chats:
            await check_and_monitor_vc(chat_id)
        # if monitor exists but task done, ensure it's restarted
        task = _monitor_tasks.get(chat_id)
        if is_enabled(chat_id) and (not task or task.done()):
            await check_and_monitor_vc(chat_id)
        return humans
    except Exception as e:
        LOGGER.error(f"[VCLOGGER] perform_vc_refresh error for {chat_id}: {e}")
        return set()

# -------------------------
# Command: /vcr e f r e s h  (admin-only) (alias /vclogger refresh)
# -------------------------
@app.on_message(filters.command("vcrefresh") & filters.group)
async def vcrefresh_cmd(_, message: Message):
    if not await _is_group_admin(message):
        return await message.reply_text("Only group admins can use this command.")
    await message.reply_text("🔄 Refreshing VC — scanning participants now...")
    humans = await perform_vc_refresh(message.chat.id)
    text = "🔄 VC Refreshed Successfully!\n\n"
    if not humans:
        text += "No human participants found in VC."
    else:
        text += f"Current Members ({len(humans)}):\n"
        # fetch names for pretty list
        entries = []
        userbot = await get_assistant(message.chat.id)
        if userbot:
            for uid in humans:
                try:
                    usr = await userbot.get_users(uid)
                    nm = usr.first_name or "ᴜɴᴋɴᴏᴡɴ"
                    if getattr(usr, "username", None):
                        entries.append(f"• {nm} (@{usr.username})")
                    else:
                        entries.append(f"• {nm} — <code>{uid}</code>")
                except Exception:
                    entries.append(f"• <code>{uid}</code>")
        text += "\n".join(entries)
    await message.reply_text(text, disable_web_page_preview=True)

# -------------------------
# /vclogger commands (admin-only)
# -------------------------
async def _is_group_admin(message: Message):
    try:
        member = await message.chat.get_member(message.from_user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

@app.on_message(filters.command("vclogger") & filters.group)
async def vclogger_cmd(_, message: Message):
    # usage: /vclogger enable|disable|status|style|cooldown|delete_after|refresh
    if not await _is_group_admin(message):
        return await message.reply_text("Only group admins can use this command.")

    args = message.text.strip().split()
    if len(args) < 2:
        return await message.reply_text(
            "Usage:\n/vclogger enable|disable|status|style <name|random>|cooldown <sec>|delete_after <sec>|refresh\n"
            "Available styles: premium, neon, royal, anime, cyber, dark, random"
        )

    action = args[1].lower()

    if action == "enable":
        enable_logger(message.chat.id)
        asyncio.create_task(check_and_monitor_vc(message.chat.id))
        return await message.reply_text("✅ Voice chat logger enabled for this group.")

    if action == "disable":
        disable_logger(message.chat.id)
        if message.chat.id in active_vc_chats:
            active_vc_chats.discard(message.chat.id)
        # cancel monitor task if exists
        task = _monitor_tasks.get(message.chat.id)
        if task and not task.done():
            try:
                task.cancel()
            except Exception:
                pass
        return await message.reply_text("❌ Voice chat logger disabled for this group.")

    if action == "status":
        enabled = is_enabled(message.chat.id)
        style = get_style(message.chat.id)
        cooldown = get_cooldown(message.chat.id)
        delete_after = get_delete_after(message.chat.id)
        return await message.reply_text(f"Enabled: {enabled}\nStyle: {style}\nCooldown: {cooldown}s\nAuto-delete: {delete_after}s")

    if action == "style":
        if len(args) < 3:
            return await message.reply_text("Specify style name or 'random'.\nAvailable: premium, neon, royal, anime, cyber, dark, random")
        style_name = args[2].lower()
        if style_name not in list(_STYLE_FUNC.keys()) + ["random"]:
            return await message.reply_text("Unknown style. See available: premium, neon, royal, anime, cyber, dark, random")
        set_style(message.chat.id, style_name)
        return await message.reply_text(f"✅ VC message style set to: {style_name}")

    if action == "cooldown" and len(args) >= 3:
        try:
            val = float(args[2])
            set_chat_cfg(message.chat.id, "cooldown", val)
            return await message.reply_text(f"Cooldown set to {val} seconds.")
        except Exception:
            return await message.reply_text("Invalid cooldown value.")

    if action == "delete_after" and len(args) >= 3:
        try:
            val = int(args[2])
            set_chat_cfg(message.chat.id, "delete_after", val)
            return await message.reply_text(f"Auto-delete set to {val} seconds.")
        except Exception:
            return await message.reply_text("Invalid delete_after value.")

    if action == "refresh":
        # same as /vcrefresh
        await message.reply_text("🔄 Refreshing VC — scanning participants now...")
        humans = await perform_vc_refresh(message.chat.id)
        text = "🔄 VC Refreshed Successfully!\n\n"
        if not humans:
            text += "No human participants found in VC."
        else:
            text += f"Current Members ({len(humans)}):\n"
            entries = []
            userbot = await get_assistant(message.chat.id)
            if userbot:
                for uid in humans:
                    try:
                        usr = await userbot.get_users(uid)
                        nm = usr.first_name or "ᴜɴᴋɴᴏᴡɴ"
                        if getattr(usr, "username", None):
                            entries.append(f"• {nm} (@{usr.username})")
                        else:
                            entries.append(f"• {nm} — <code>{uid}</code>")
                    except Exception:
                        entries.append(f"• <code>{uid}</code>")
            text += "\n".join(entries)
        await message.reply_text(text, disable_web_page_preview=True)
        return

    return await message.reply_text("Unknown vclogger command option.")

# -------------------------
# Optional: start monitors for enabled chats at startup
# -------------------------
async def start_monitors_from_config():
    try:
        for k, v in _config.items():
            try:
                cid = int(k)
                if v.get("enabled"):
                    asyncio.create_task(check_and_monitor_vc(cid))
            except Exception:
                continue
    except Exception as e:
        LOGGER.error(f"[VCLOGGER] start monitors err: {e}")

# kick off startup monitors (no await)
asyncio.create_task(start_monitors_from_config())