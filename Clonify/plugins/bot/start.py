import time
import random
import asyncio
from pyrogram import filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from youtubesearchpython.__future__ import VideosSearch

import config
from Clonify import app
from Clonify.misc import _boot_
from Clonify.plugins.sudo.sudoers import sudoers_list
from Clonify.utils.database import get_served_chats, get_served_users, get_sudoers
from Clonify.utils import bot_sys_stats
from Clonify.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_lang,
    is_banned_user,
    is_on_off,
)
from Clonify.utils.decorators.language import LanguageStart
from Clonify.utils.formatters import get_readable_time
from Clonify.utils.inline import help_pannel, private_panel, start_panel
from config import BANNED_USERS, STREAMI_PICS, GREET
from strings import get_string


# ======================================
# PRIVATE START
# ======================================
@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):

    loading_1 = await message.reply_text(random.choice(GREET))
    await add_served_user(message.from_user.id)

    # Loading animation
    for t in ["<b>ʟᴏᴀᴅɪɴɢ</b>", "<b>ʟᴏᴀᴅɪɴɢ.</b>", "<b>ʟᴏᴀᴅɪɴɢ..</b>", "<b>ʟᴏᴀᴅɪɴɢ...</b>"]:
        await asyncio.sleep(0.1)
        await loading_1.edit_text(t)

    await loading_1.delete()

    # /start parameters
    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]

        # Help menu
        if name[0:4] == "help":
            keyboard = help_pannel(_)
            return await message.reply_video(
                random.choice(STREAMI_PICS),
                caption=_["help_1"].format(config.SUPPORT_CHAT),
                reply_markup=keyboard,
                has_spoiler=True,   # SPOILER
            )

        # Sudo list
        if name[0:3] == "sud":
            await sudoers_list(client=client, message=message, _=_)
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=f"✦ {message.from_user.mention} checked <b>sudolist</b>.\n\n<b>User ID:</b> <code>{message.from_user.id}</code>\n<b>Username:</b> @{message.from_user.username}",
                )
            return

        # Info request (YouTube)
        if name[0:3] == "inf":
            m = await message.reply_text("🔎")
            query = (str(name)).replace("info_", "", 1)
            query = f"https://www.youtube.com/watch?v={query}"
            results = VideosSearch(query, limit=1)

            for result in (await results.next())["result"]:
                title = result["title"]
                duration = result["duration"]
                views = result["viewCount"]["short"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                channellink = result["channel"]["link"]
                channel = result["channel"]["name"]
                link = result["link"]
                published = result["publishedTime"]

            searched_text = _["start_6"].format(
                title, duration, views, published, channellink, channel, app.mention
            )
            key = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(text=_["S_B_8"], url=link),
                        InlineKeyboardButton(text=_["S_B_9"], url=config.SUPPORT_CHAT),
                    ],
                ]
            )

            await m.delete()
            await app.send_photo(
                chat_id=message.chat.id,
                photo=thumbnail,
                caption=searched_text,
                reply_markup=key,
                has_spoiler=True,   # SPOILER OPTIONAL, YOU WANTED ON START IMAGE ONLY
            )

            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOGGER_ID,
                    text=f"✦ {message.from_user.mention} checked track info.\n\n<b>User ID:</b> <code>{message.from_user.id}</code>\n<b>Username:</b> @{message.from_user.username}",
                )

    # Default private start
    else:
        out = private_panel(_)
        await message.reply_video(
            random.choice(STREAMI_PICS),
            caption=_["start_2"].format(message.from_user.mention, app.mention),
            reply_markup=InlineKeyboardMarkup(out),
            has_spoiler=True,  # ★ SPOILER ON START IMAGE
        )

        if await is_on_off(2):
            return await app.send_message(
                chat_id=config.LOGGER_ID,
                text=f"✦ {message.from_user.mention} started the bot.\n\n<b>User ID:</b> <code>{message.from_user.id}</code>\n<b>Username:</b> @{message.from_user.username}",
            )


# ======================================
# GROUP START
# ======================================
@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    out = start_panel(_)
    uptime = int(time.time() - _boot_)

    await message.reply_video(
        random.choice(STREAMI_PICS),
        caption=_["start_1"].format(app.mention, get_readable_time(uptime)),
        reply_markup=InlineKeyboardMarkup(out),
        has_spoiler=True,  # ★ SPOILER ON START IMAGE (GROUP)
    )

    return await add_served_chat(message.chat.id)


# ======================================
# WELCOME NEW MEMBERS
# ======================================
@app.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)

            if await is_banned_user(member.id):
                try:
                    await message.chat.ban_member(member.id)
                except:
                    pass

            if member.id == app.id:
                if message.chat.type != ChatType.SUPERGROUP:
                    await message.reply_text(_["start_4"])
                    return await app.leave_chat(message.chat.id)

                if message.chat.id in await blacklisted_chats():
                    await message.reply_text(
                        _["start_5"].format(
                            app.mention,
                            f"https://t.me/{app.username}?start=sudolist",
                            config.SUPPORT_CHAT,
                        ),
                        disable_web_page_preview=True,
                    )
                    return await app.leave_chat(message.chat.id)

                out = start_panel(_)
                await message.reply_text(
                    text=_["start_3"].format(
                        message.from_user.mention,
                        app.mention,
                        message.chat.title,
                        app.mention,
                    ),
                    reply_markup=InlineKeyboardMarkup(out),
                )

                await add_served_chat(message.chat.id)
                await message.stop_propagation()

        except Exception as ex:
            print(ex)