""" vclogger.py — Clean, robust full rewrite (Option A)

This is a complete, syntactically-correct rewrite in a plain "normal" Python style.

Reliable admin check (uses app.get_chat_member with fallback)

Monitor loop uses a get_assistant(chat_id) placeholder (adapt this to your project)

Persistent JSON config for per-chat settings

Six message styles (triple-quoted, safe) + random option

Cooldown, auto-delete, manual refresh, callback handlers

Clear logging and safe exception handling


Integration notes:

Replace get_assistant with your project's assistant lookup if necessary.

Ensure app imported from Clonify is your running Bot client.


"""

import asyncio import json import logging import random import time from datetime import datetime, timezone from typing import Dict, Set, Optional

from pyrogram import filters from pyrogram.types import ( Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ) from pyrogram.raw import functions

from Clonify import app

LOGGER = logging.getLogger(name)

-------------------------

Runtime state

-------------------------

vc_active_users: Dict[int, Set[int]] = {} active_vc_chats: Set[int] = set() last_sent_time: Dict[int, float] = {} recent_join_times: Dict[int, Dict[int, float]] = {} _monitor_tasks: Dict[int, asyncio.Task] = {}

-------------------------

Persistent config (JSON)

-------------------------

CONFIG_FILE = "vclogger_config.json" DEFAULT_COOLDOWN = 2.0 DEFAULT_DELETE_AFTER = 10

def load_config() -> dict: try: with open(CONFIG_FILE, "r") as f: return json.load(f) except FileNotFoundError: return {} except Exception: LOGGER.exception("[VCLOGGER] Failed to load config") return {}

def save_config(data: dict) -> None: try: with open(CONFIG_FILE, "w") as f: json.dump(data, f, indent=2) except Exception: LOGGER.exception("[VCLOGGER] Failed to save config")

_config = load_config()

def get_chat_cfg(chat_id: int) -> dict: return _config.get(str(chat_id), {})

def set_chat_cfg(chat_id: int, key: str, value) -> None: cid = str(chat_id) if cid not in _config: _config[cid] = {} _config[cid][key] = value save_config(_config)

def is_enabled(chat_id: int) -> bool: return bool(get_chat_cfg(chat_id).get("enabled", False))

def enable_logger(chat_id: int) -> None: set_chat_cfg(chat_id, "enabled", True)

def disable_logger(chat_id: int) -> None: cid = str(chat_id) if cid in _config: _config[cid]["enabled"] = False save_config(_config)

def get_cooldown(chat_id: int) -> float: try: return float(get_chat_cfg(chat_id).get("cooldown", DEFAULT_COOLDOWN)) except Exception: return DEFAULT_COOLDOWN

def get_delete_after(chat_id: int) -> int: try: return int(get_chat_cfg(chat_id).get("delete_after", DEFAULT_DELETE_AFTER)) except Exception: return DEFAULT_DELETE_AFTER

def get_style(chat_id: int) -> str: return get_chat_cfg(chat_id).get("style", "premium")

def set_style(chat_id: int, style_name: str) -> None: set_chat_cfg(chat_id, "style", style_name)

-------------------------

Styles (safe triple-quoted strings)

-------------------------

def style_premium(name, username, user_id, total, join_time_iso): return (f""" 💫 <b>New Member Joined VC</b>

👤 <b>Name:</b> {name} 🔗 <b>Username:</b> {username} 🆔 <b>ID:</b> <code>{user_id}</code>

👥 <b>Total in VC:</b> <code>{total}</code> 🕒 <b>Join Time:</b> {join_time_iso}

✨ <i>Welcome to the voice chat!</i> """, "✨")

def style_neon(name, username, user_id, total, join_time_iso): return (f""" 💠 <b>NEON VC ALERT</b>

👤 <b>Name:</b> {name} 🔗 <b>Username:</b> {username} 🆔 <b>ID:</b> <code>{user_id}</code>

👥 <b>Total in VC:</b> <code>{total}</code> 🕒 <b>Time:</b> {join_time_iso}

⚡ <i>Your presence makes the VC shine!</i> """, "⚡")

def style_royal(name, username, user_id, total, join_time_iso): return (f""" 👑 <b>ROYAL VC ENTRY</b>

✨ <b>Name:</b> {name} 📛 <b>Username:</b> {username} 🆔 <b>ID:</b> <code>{user_id}</code>

👥 <b>Total in VC:</b> <code>{total}</code> 🕒 <b>Joined:</b> {join_time_iso}

💛 <i>Welcome to the golden hall.</i> """, "💛")

def style_anime(name, username, user_id, total, join_time_iso): return (f""" 🌸 <b>ANIME VC ENTRY</b>

👤 <b>Name:</b> {name} 🌐 <b>Username:</b> {username} 🆔 <b>ID:</b> <code>{user_id}</code>

👥 <b>Total in VC:</b> <code>{total}</code> 🕒 <b>Time:</b> {join_time_iso}

💮 <i>Konnichiwa~ enjoy the VC!</i> """, "💮")

def style_cyber(name, username, user_id, total, join_time_iso): return (f""" 🧬 <b>CYBER MODE ACTIVATED</b>

👤 <b>User:</b> {name} 📡 <b>Net Tag:</b> {username} 🆔 <b>Code:</b> <code>{user_id}</code>

👥 <b>Total in VC:</b> <code>{total}</code> 🕒 <b>Time:</b> {join_time_iso}

⚙️ <i>User connected to VC network.</i> """, "⚙️")

def style_dark(name, username, user_id, total, join_time_iso): return (f""" 🔥 <b>DARK SOUL ENTERED VC</b>

😈 <b>Name:</b> {name} 🔗 <b>Tag:</b> {username} 🆔 <b>ID:</b> <code>{user_id}</code>

👥 <b>Total in VC:</b> <code>{total}</code> 🕒 <b>Time:</b> {join_time_iso}

🌑 <i>The VC grows darker...</i> """, "🌑")

_STYLE_FUNC = { "premium": style_premium, "neon": style_neon, "royal": style_royal, "anime": style_anime, "cyber": style_cyber, "dark": style_dark, }

-------------------------

Helper — fetch participants (raw)

-------------------------

async def get_group_call_participants(userbot, peer): try: full_chat = await userbot.invoke(functions.channels.GetFullChannel(channel=peer)) if not hasattr(full_chat.full_chat, "call") or not full_chat.full_chat.call: return [] call = full_chat.full_chat.call participants = await userbot.invoke( functions.phone.GetGroupParticipants(call=call, ids=[], sources=[], offset="", limit=100) ) return getattr(participants, "participants", []) except Exception as e: error_msg = str(e).upper() if any(x in error_msg for x in ["GROUPCALL_NOT_FOUND", "CALL_NOT_FOUND", "NO_GROUPCALL"]): return [] LOGGER.exception(f"[VC LOGGER] Error fetching participants: {e}") return []

-------------------------

get_assistant placeholder

-------------------------

async def get_assistant(chat_id: int): """ Return an assistant (userbot) client instance able to call raw functions. Replace this with your project's implementation that returns the appropriate assistant client for the chat. Return None if not available. """ # TODO: Replace with your own assistant lookup if necessary try: return app except Exception: return None

-------------------------

Cooldown guard

-------------------------

def can_send_alert(chat_id: int) -> bool: now = time.time() cd = get_cooldown(chat_id) last = last_sent_time.get(chat_id, 0) if now - last >= cd: last_sent_time[chat_id] = now return True return False

-------------------------

Monitor loop

-------------------------

async def monitor_vc_chat(chat_id: int): userbot = await get_assistant(chat_id) if not userbot: LOGGER.warning(f"[VCLOGGER] No assistant available for {chat_id}") return

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

            # filter joins: only humans
            human_joined = set()
            for uid in joined:
                try:
                    usr = await userbot.get_users(uid)
                    if getattr(usr, "is_bot", False):
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

        except Exception:
            LOGGER.exception(f"[VC LOGGER] Error in monitor loop for {chat_id}")

        await asyncio.sleep(2)
finally:
    _monitor_tasks.pop(chat_id, None)
    active_vc_chats.discard(chat_id)

-------------------------

Start monitor if needed

-------------------------

async def check_and_monitor_vc(chat_id: int) -> None: userbot = await get_assistant(chat_id) if not userbot: return

try:
    peer = await userbot.resolve_peer(chat_id)
    participants = await get_group_call_participants(userbot, peer)

    if participants and chat_id not in active_vc_chats and is_enabled(chat_id):
        active_vc_chats.add(chat_id)
        task = asyncio.create_task(monitor_vc_chat(chat_id))
        _monitor_tasks[chat_id] = task

except Exception:
    LOGGER.exception(f"[VC LOGGER] check_and_monitor error for {chat_id}")

-------------------------

Delete after delay helper

-------------------------

async def delete_after_delay(msg, delay: int): try: await asyncio.sleep(delay) await msg.delete() except Exception: pass

-------------------------

Time helper

-------------------------

def iso_local_time() -> str: now = datetime.now(timezone.utc).astimezone() return now.strftime("%Y-%m-%d %H:%M:%S %Z")

-------------------------

Message helpers

-------------------------

async def handle_user_join(chat_id: int, user_id: int, userbot) -> None: try: user = await userbot.get_users(user_id) name = (user.first_name or "ᴜɴᴋɴᴏᴡɴ").strip() username = f"@{user.username}" if getattr(user, "username", None) else "ɴᴏ ᴜsᴇʀɴᴀᴍᴇ" mention = f'<a href="tg://user?id={user_id}">{name}</a>'

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
        [InlineKeyboardButton("🔍 Profile", url=f"tg://user?id={user_id}")],
    ])

    sent = await app.send_message(chat_id, text, reply_markup=keyboard, disable_web_page_preview=True)
    asyncio.create_task(delete_after_delay(sent, get_delete_after(chat_id)))

except Exception:
    LOGGER.exception(f"[VC LOGGER] Join msg error for {user_id} in {chat_id}")

async def handle_user_leave(chat_id: int, user_id: int, userbot) -> None: try: user = await userbot.get_users(user_id) name = (user.first_name or "ᴜɴᴋɴᴏᴡɴ").strip() username = f"@{user.username}" if getattr(user, "username", None) else "ɴᴏ ᴜsᴇʀɴᴀᴍᴇ" mention = f'<a href="tg://user?id={user_id}">{name}</a>'

total = max(0, len(vc_active_users.get(chat_id, set())) - 1)
    leave_time_iso = iso_local_time()

    style = get_style(chat_id)
    if style == "random":
        style = random.choice(list(_STYLE_FUNC.keys()))
    style_func = _STYLE_FUNC.get(style, style_premium)
    text, footer = style_func(mention, username, user_id, total, leave_time_iso)

    # Modify text to indicate leave
    text = text.replace("New Member Joined VC", "Member left the voice chat")

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔍 Profile", url=f"tg://user?id={user_id}")]])

    sent = await app.send_message(chat_id, text, reply_markup=keyboard, disable_web_page_preview=True)
    asyncio.create_task(delete_after_delay(sent, get_delete_after(chat_id)))

except Exception:
    LOGGER.exception(f"[VC LOGGER] Leave msg error for {user_id} in {chat_id}")

-------------------------

Build members text

-------------------------

async def build_vc_members_text(chat_id: int) -> str: userbot = await get_assistant(chat_id) if not userbot: return "Assistant not available."

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
    header = f"👥 <b>Current VC Members — {len(lines)}</b>

" return header + " ".join(lines) except Exception: LOGGER.exception("[VCLOGGER] build_vc_members_text err") return "Failed to fetch VC participants."

-------------------------

Callbacks

-------------------------

@app.on_callback_query(filters.regex(r"^vclist:")) async def vclist_cb(, cb: CallbackQuery): try: await cb.answer() parts = (cb.data or "").split(":") if len(parts) != 2: return chat_id = int(parts[1]) text = await build_vc_members_text(chat_id) try: await cb.message.reply_text(text, disable_web_page_preview=True) except Exception: await cb.edit_message_text(text, disable_web_page_preview=True) except Exception: LOGGER.exception("[VCLOGGER] vclist cb err")

@app.on_callback_query(filters.regex(r"^vcrefresh_cb:")) async def vcrefresh_cb(, cb: CallbackQuery): try: await cb.answer("Refreshing VC…", show_alert=False) parts = (cb.data or "").split(":") if len(parts) != 2: return chat_id = int(parts[1]) await perform_vc_refresh(chat_id) text = await build_vc_members_text(chat_id) await cb.message.reply_text("🔄 VC refreshed.

" + text, disable_web_page_preview=True) except Exception: LOGGER.exception("[VCLOGGER] vcrefresh cb err")

-------------------------

Manual refresh

-------------------------

async def perform_vc_refresh(chat_id: int) -> Set[int]: userbot = await get_assistant(chat_id) if not userbot: return set()

try:
    peer = await userbot.resolve_peer(chat_id)
    participants = await get_group_call_participants(userbot, peer)
    new_users = {p.peer.user_id for p in participants if hasattr(p, "peer")}
    humans = set()
    for uid in new_users:
        try:
            usr = await userbot.get_users(uid)
            if getattr(usr, "is_bot", False):
                continue
            humans.add(uid)
        except Exception:
            continue
    vc_active_users[chat_id] = humans
    task = _monitor_tasks.get(chat_id)
    if is_enabled(chat_id) and (not task or task.done()):
        await check_and_monitor_vc(chat_id)
    return humans
except Exception:
    LOGGER.exception(f"[VCLOGGER] perform_vc_refresh error for {chat_id}")
    return set()

-------------------------

Commands

-------------------------

async def _is_group_admin(message: Message) -> bool: """ Reliable admin check using app.get_chat_member. Returns True if sender is admin or creator. """ try: member = await app.get_chat_member(message.chat.id, message.from_user.id) return member.status in ("administrator", "creator") except Exception: try: member = await message.chat.get_member(message.from_user.id) return member.status in ("administrator", "creator") except Exception: return False

@app.on_message(filters.command("vcrefresh") & filters.group) async def vcrefresh_cmd(_, message: Message): if not await _is_group_admin(message): return await message.reply_text("Only group admins can use this command.") await message.reply_text("🔄 Refreshing VC — scanning participants now...") humans = await perform_vc_refresh(message.chat.id) text = "🔄 VC Refreshed Successfully!

" if not humans: text += "No human participants found in VC." else: text += f"Current Members ({len(humans)}): " entries = [] userbot = await get_assistant(message.chat.id) if userbot: for uid in humans: try: usr = await userbot.get_users(uid) nm = usr.first_name or "ᴜɴᴋɴᴏᴡɴ" if getattr(usr, "username", None): entries.append(f"• {nm} (@{usr.username})") else: entries.append(f"• {nm} — <code>{uid}</code>") except Exception: entries.append(f"• <code>{uid}</code>") text += " ".join(entries) await message.reply_text(text, disable_web_page_preview=True)

@app.on_message(filters.command("vclogger") & filters.group) async def vclogger_cmd(_, message: Message): if not await _is_group_admin(message): return await message.reply_text("Only group admins can use this command.")

args = message.text.strip().split()
if len(args) < 2:
    return await message.reply_text(
        "Usage:

/vclogger enable|disable|status|style <name|random>|cooldown <sec>|delete_after <sec>|refresh " "Available styles: premium, neon, royal, anime, cyber, dark, random" )

action = args[1].lower()

if action == "enable":
    enable_logger(message.chat.id)
    asyncio.create_task(check_and_monitor_vc(message.chat.id))
    return await message.reply_text("✅ Voice chat logger enabled for this group.")

if action == "disable":
    disable_logger(message.chat.id)
    if message.chat.id in active_vc_chats:
        active_vc_chats.discard(message.chat.id)
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
    return await message.reply_text(f"Enabled: {enabled}

Style: {style} Cooldown: {cooldown}s Auto-delete: {delete_after}s")

if action == "style":
    if len(args) < 3:
        return await message.reply_text("Specify style name or 'random'.

Available: premium, neon, royal, anime, cyber, dark, random") style_name = args[2].lower() if style_name not in list(_STYLE_FUNC.keys()) + ["random"]: return await message.reply_text("Unknown style. See available: premium, neon, royal, anime, cyber, dark, random") set_style(message.chat.id, style_name) return await message.reply_text(f"✅ VC message style set to: {style_name}")

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
    await message.reply_text("🔄 Refreshing VC — scanning participants now...")
    humans = await perform_vc_refresh(message.chat.id)
    text = "🔄 VC Refreshed Successfully!

" if not humans: text += "No human participants found in VC." else: text += f"Current Members ({len(humans)}): " entries = [] userbot = await get_assistant(message.chat.id) if userbot: for uid in humans: try: usr = await userbot.get_users(uid) nm = usr.first_name or "ᴜɴᴋɴᴏᴡɴ" if getattr(usr, "username", None): entries.append(f"• {nm} (@{usr.username})") else: entries.append(f"• {nm} — <code>{uid}</code>") except Exception: entries.append(f"• <code>{uid}</code>") text += " ".join(entries) await message.reply_text(text, disable_web_page_preview=True) return

return await message.reply_text("Unknown vclogger command option.")

-------------------------

Startup monitors

-------------------------

async def start_monitors_from_config(): try: for k, v in _config.items(): try: cid = int(k) if v.get("enabled"): asyncio.create_task(check_and_monitor_vc(cid)) except Exception: continue except Exception: LOGGER.exception("[VCLOGGER] start monitors err")

schedule startup (best-effort)

try: asyncio.create_task(start_monitors_from_config()) except Exception: # if event loop not running at import time, ignore; function can be called later pass

End of file