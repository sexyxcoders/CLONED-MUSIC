import os
from random import randint
from typing import Union

from pyrogram.types import InlineKeyboardMarkup

import config
from Clonify import Carbon, YouTube, app
from Clonify.core.call import PRO
from Clonify.misc import db
from Clonify.utils.database import add_active_video_chat, is_active_chat
from Clonify.utils.exceptions import AssistantErr
from Clonify.utils.inline import aq_markup, close_markup, stream_markup
from Clonify.utils.stream.queue import put_queue, put_queue_index
from Clonify.utils.pastebin import PROBin
from Clonify.utils.thumbnails import get_thumb

# ------------------------------
# Thumbnail Generator (safe)
# ------------------------------
def safe_generate_thumbnail(vidid: str, title="Unknown", artist="Unknown", provider_thumb: str = None) -> str:
    """
    Generate a thumbnail synchronously and return the file path.
    If thumbnail generation fails, return the best available fallback:
      1) provider_thumb (if provided and exists)
      2) config.TELEGRAM_AUDIO_URL or config.SOUNCLOUD_IMG_URL or config.STREAM_IMG_URL (if available)
      3) './downloads/default.jpg' (local fallback)
    """
    try:
        os.makedirs("./thumbnails", exist_ok=True)
        album_art_path = f"./downloads/{vidid}.jpg"
        if not os.path.isfile(album_art_path):
            # fallback to downloads default (keep as local fallback)
            album_art_path = "./downloads/default.jpg"
        output_path = f"./thumbnails/{vidid}.png"

        # call existing wrapper get_thumb() from thumbnails.py
        # signature: get_thumb(album_art_path, song_title=..., artist_name=..., output_path=..., style="A", reference_image=None)
        try:
            # attempt to create thumbnail file
            ret = get_thumb(
                album_art_path,
                song_title=title,
                artist_name=artist,
                output_path=output_path,
                style="A"
            )
            # get_thumb in your thumbnails should return the path; otherwise use output_path
            result_path = ret if isinstance(ret, str) else output_path
        except Exception as e:
            # swallowed so stream doesn't fail — log and continue to fallback
            print(f"[thumbnail] get_thumb() raised: {e}")
            result_path = None

        # verify output exists
        if result_path and os.path.isfile(result_path):
            return result_path

    except Exception as e:
        # any filesystem error; print for debugging and continue to fallback
        print(f"[thumbnail] unexpected error creating thumbnail: {e}")

    # FALLBACK CHAIN (ensure we return an existing path or a URL)
    # 1) provider thumbnail (a URL or local path passed by youtube/soundcloud)
    if provider_thumb:
        # if it's a local file path and exists, return it
        if os.path.isfile(provider_thumb):
            return provider_thumb
        # if it's a URL, return it (pyrogram send_photo accepts URL)
        if provider_thumb.startswith("http://") or provider_thumb.startswith("https://"):
            return provider_thumb

    # 2) configured fallback images from config (try several candidates)
    for candidate in (
        getattr(config, "TELEGRAM_AUDIO_URL", None),
        getattr(config, "SOUNCLOUD_IMG_URL", None),
        getattr(config, "STREAM_IMG_URL", None),
        getattr(config, "TELEGRAM_VIDEO_URL", None),
        getattr(config, "SUPPORT_CHAT", None),
    ):
        if not candidate:
            continue
        # local file?
        if isinstance(candidate, str) and os.path.isfile(candidate):
            return candidate
        # url?
        if isinstance(candidate, str) and (candidate.startswith("http://") or candidate.startswith("https://")):
            return candidate

    # 3) local default placeholder (ensure it exists; otherwise create a tiny placeholder)
    local_default = "./downloads/default.jpg"
    if os.path.isfile(local_default):
        return local_default

    # last resort: create a tiny red image and return its path
    try:
        from PIL import Image
        tiny_path = "./thumbnails/fallback_default.png"
        if not os.path.isfile(tiny_path):
            Image.new("RGB", (640, 360), (44, 9, 8)).save(tiny_path)
        return tiny_path
    except Exception as e:
        # if pillow isn't available, return a plain string; caller (app.send_photo) will likely fail but we tried
        print(f"[thumbnail] failed to create tiny fallback image: {e}")
        return "./downloads/default.jpg"

# ------------------------------
# Main Stream Function
# ------------------------------
async def stream(
    _,
    mystic,
    user_id,
    result,
    chat_id,
    user_name,
    original_chat_id,
    video: Union[bool, str] = None,
    streamtype: Union[bool, str] = None,
    spotify: Union[bool, str] = None,
    forceplay: Union[bool, str] = None,
):
    if not result:
        return

    if forceplay:
        await PRO.force_stop_stream(chat_id)

    # --------------------------
    # Playlist Handling
    # --------------------------
    if streamtype == "playlist":
        msg = f"{_['play_19']}\n\n"
        count = 0

        for search in result:
            if int(count) == config.PLAYLIST_FETCH_LIMIT:
                continue
            try:
                title, duration_min, duration_sec, thumbnail, vidid = await YouTube.details(
                    search, False if spotify else True
                )
            except Exception:
                continue

            if duration_sec is None or duration_sec > config.DURATION_LIMIT:
                continue

            if await is_active_chat(chat_id):
                await put_queue(
                    chat_id, original_chat_id, f"vid_{vidid}",
                    title, duration_min, user_name, vidid, user_id,
                    "video" if video else "audio"
                )
                position = len(db.get(chat_id)) - 1
                count += 1
                msg += f"{count}. {title[:70]}\n{_['play_20']} {position}\n\n"
            else:
                if not forceplay:
                    db[chat_id] = []
                try:
                    file_path, direct = await YouTube.download(
                        vidid, mystic, video=True if video else None, videoid=True
                    )
                except Exception:
                    raise AssistantErr(_["play_14"])

                await PRO.join_call(
                    chat_id, original_chat_id, file_path,
                    video=True if video else None, image=thumbnail
                )
                await put_queue(
                    chat_id, original_chat_id,
                    file_path if direct else f"vid_{vidid}",
                    title, duration_min, user_name, vidid, user_id,
                    "video" if video else "audio",
                    forceplay=forceplay
                )

                img = safe_generate_thumbnail(vidid, title, user_name, provider_thumb=thumbnail)
                button = stream_markup(_, chat_id)
                try:
                    run = await app.send_photo(
                        original_chat_id,
                        photo=img,
                        caption=_["stream_1"].format(
                            f"https://t.me/{app.username}?start=info_{vidid}",
                            title[:23], duration_min, user_name
                        ),
                        reply_markup=InlineKeyboardMarkup(button)
                    )
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "stream"
                except Exception as e:
                    print(f"[stream][playlist] failed to send photo: {e}")
                    # still keep queue updated — do not raise

        if count == 0:
            return

        link = await PROBin(msg)
        lines = msg.count("\n")
        car = os.linesep.join(msg.split(os.linesep)[:17]) if lines >= 17 else msg
        carbon = await Carbon.generate(car, randint(100, 10000000))
        upl = close_markup(_)
        return await app.send_photo(
            original_chat_id,
            photo=carbon,
            caption=_["play_21"].format(position, link),
            reply_markup=upl
        )

    # --------------------------
    # Single YouTube Video
    # --------------------------
    elif streamtype == "youtube":
        link = result["link"]
        vidid = result["vidid"]
        title = result["title"].title()
        duration_min = result["duration_min"]
        thumbnail = result["thumb"]
        status = True if video else None

        try:
            file_path, direct = await YouTube.download(
                vidid, mystic, videoid=True, video=status
            )
        except Exception:
            raise AssistantErr(_["play_14"])

        if await is_active_chat(chat_id):
            await put_queue(
                chat_id, original_chat_id,
                file_path if direct else f"vid_{vidid}",
                title, duration_min, user_name, vidid, user_id,
                "video" if video else "audio"
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await app.send_message(
                chat_id=original_chat_id,
                text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                reply_markup=InlineKeyboardMarkup(button)
            )
        else:
            if not forceplay:
                db[chat_id] = []
            await PRO.join_call(
                chat_id, original_chat_id, file_path,
                video=status, image=thumbnail
            )
            await put_queue(
                chat_id, original_chat_id,
                file_path if direct else f"vid_{vidid}",
                title, duration_min, user_name, vidid, user_id,
                "video" if video else "audio",
                forceplay=forceplay
            )

            img = safe_generate_thumbnail(vidid, title, user_name, provider_thumb=thumbnail)
            button = stream_markup(_, chat_id)
            try:
                run = await app.send_photo(
                    original_chat_id,
                    photo=img,
                    caption=_["stream_1"].format(
                        f"https://t.me/{app.username}?start=info_{vidid}",
                        title[:23], duration_min, user_name
                    ),
                    reply_markup=InlineKeyboardMarkup(button)
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"
            except Exception as e:
                print(f"[stream][youtube] failed to send photo: {e}")
                # fallback: try sending provider thumbnail if different
                if thumbnail and thumbnail != img:
                    try:
                        run = await app.send_photo(original_chat_id, photo=thumbnail,
                                                   caption=_["stream_1"].format(
                                                       f"https://t.me/{app.username}?start=info_{vidid}",
                                                       title[:23], duration_min, user_name
                                                   ), reply_markup=InlineKeyboardMarkup(button))
                        db[chat_id][0]["mystic"] = run
                        db[chat_id][0]["markup"] = "stream"
                    except Exception as e2:
                        print(f"[stream][youtube] provider thumbnail also failed: {e2}")

    # --------------------------
    # SoundCloud
    # --------------------------
    elif streamtype == "soundcloud":
        file_path = result["filepath"]
        title = result["title"]
        duration_min = result["duration_min"]

        if await is_active_chat(chat_id):
            await put_queue(
                chat_id, original_chat_id, file_path,
                title, duration_min, user_name, streamtype, user_id, "audio"
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await app.send_message(
                chat_id=original_chat_id,
                text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                reply_markup=InlineKeyboardMarkup(button)
            )
        else:
            if not forceplay:
                db[chat_id] = []
            await PRO.join_call(chat_id, original_chat_id, file_path, video=None)
            await put_queue(
                chat_id, original_chat_id, file_path,
                title, duration_min, user_name, streamtype, user_id, "audio",
                forceplay=forceplay
            )
            button = stream_markup(_, chat_id)
            # use configured soundcloud image (URL) or fallback
            img_to_send = getattr(config, "SOUNCLOUD_IMG_URL", None) or safe_generate_thumbnail("sc_"+str(randint(10000,99999)), title, user_name)
            try:
                run = await app.send_photo(
                    original_chat_id,
                    photo=img_to_send,
                    caption=_["stream_1"].format(config.SUPPORT_CHAT, title[:23], duration_min, user_name),
                    reply_markup=InlineKeyboardMarkup(button)
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            except Exception as e:
                print(f"[stream][soundcloud] failed to send photo: {e}")

    # --------------------------
    # Telegram
    # --------------------------
    elif streamtype == "telegram":
        file_path = result["path"]
        link = result["link"]
        title = result["title"].title()
        duration_min = result["dur"]
        status = True if video else None

        if await is_active_chat(chat_id):
            await put_queue(
                chat_id, original_chat_id, file_path,
                title, duration_min, user_name, streamtype, user_id,
                "video" if video else "audio"
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await app.send_message(
                chat_id=original_chat_id,
                text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                reply_markup=InlineKeyboardMarkup(button)
            )
        else:
            if not forceplay:
                db[chat_id] = []
            await PRO.join_call(chat_id, original_chat_id, file_path, video=status)
            await put_queue(
                chat_id, original_chat_id, file_path,
                title, duration_min, user_name, streamtype, user_id,
                "video" if video else "audio",
                forceplay=forceplay
            )
            if video:
                await add_active_video_chat(chat_id)
            button = stream_markup(_, chat_id)
            img_to_send = config.TELEGRAM_VIDEO_URL if video else config.TELEGRAM_AUDIO_URL
            try:
                run = await app.send_photo(
                    original_chat_id,
                    photo=img_to_send,
                    caption=_["stream_1"].format(link, title[:23], duration_min, user_name),
                    reply_markup=InlineKeyboardMarkup(button)
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            except Exception as e:
                print(f"[stream][telegram] failed to send photo: {e}")

    # --------------------------
    # Live YouTube
    # --------------------------
    elif streamtype == "live":
        link = result["link"]
        vidid = result["vidid"]
        title = result["title"].title()
        thumbnail = result.get("thumb")
        duration_min = "Live Track"
        status = True if video else None

        if await is_active_chat(chat_id):
            await put_queue(
                chat_id, original_chat_id, f"live_{vidid}",
                title, duration_min, user_name, vidid, user_id,
                "video" if video else "audio"
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await app.send_message(
                chat_id=original_chat_id,
                text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                reply_markup=InlineKeyboardMarkup(button)
            )
        else:
            if not forceplay:
                db[chat_id] = []
            n, file_path = await YouTube.video(link)
            if n == 0:
                raise AssistantErr(_["str_3"])
            await PRO.join_call(
                chat_id, original_chat_id, file_path,
                video=status, image=thumbnail if thumbnail else None
            )
            await put_queue(
                chat_id, original_chat_id, f"live_{vidid}",
                title, duration_min, user_name, vidid, user_id,
                "video" if video else "audio",
                forceplay=forceplay
            )
            img = safe_generate_thumbnail(vidid, title, user_name, provider_thumb=thumbnail)
            button = stream_markup(_, chat_id)
            try:
                run = await app.send_photo(
                    original_chat_id,
                    photo=img,
                    caption=_["stream_1"].format(
                        f"https://t.me/{app.username}?start=info_{vidid}",
                        title[:23], duration_min, user_name
                    ),
                    reply_markup=InlineKeyboardMarkup(button)
                )
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
            except Exception as e:
                print(f"[stream][live] failed to send photo: {e}")

    # --------------------------
    # Index / m3u8
    # --------------------------
    elif streamtype == "index":
        link = result
        title = "ɪɴᴅᴇx ᴏʀ ᴍ3ᴜ8 ʟɪɴᴋ"
        duration_min = "00:00"

        if await is_active_chat(chat_id):
            await put_queue_index(
                chat_id, original_chat_id, "index_url",
                title, duration_min, user_name, link,
                "video" if video else "audio"
            )
            position = len(db.get(chat_id)) - 1
            button = aq_markup(_, chat_id)
            await mystic.edit_text(
                text=_["queue_4"].format(position, title[:27], duration_min, user_name),
                reply_markup=InlineKeyboardMarkup(button)
            )
        else:
            if not forceplay:
                db[chat_id] = []
            await PRO.join_call(
                chat_id, original_chat_id, link,
                video=True if video else None
            )
            await put_queue_index(
                chat_id, original_chat_id, "index_url",
                title, duration_min, user_name, link,
                "video" if video else "audio",
                forceplay=forceplay
            )
            button = stream_markup(_, chat_id)
            run = await app.send_photo(
                original_chat_id,
                photo=config.STREAM_IMG_URL,
                caption=_["stream_2"].format(user_name),
                reply_markup=InlineKeyboardMarkup(button)
            )
            db[chat_id][0]["mystic"] = run
            db[chat_id][0]["markup"] = "tg"
            await mystic.delete()