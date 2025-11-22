import os
from random import randint
from typing import Union, Optional

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

# third-party for downloading remote thumbnails
try:
    import requests
except Exception:
    requests = None

# ------------------------------
# Helper: Download provider thumbnail
# ------------------------------
def download_provider_thumbnail(url: str, vidid: str) -> str:
    """
    Download provider thumbnail (URL) into ./downloads/{vidid}.jpg.
    Returns the local path (or './downloads/default.jpg' on failure).
    """
    try:
        os.makedirs("./downloads", exist_ok=True)
        out_path = f"./downloads/{vidid}.jpg"

        # if file already exists, return it
        if os.path.isfile(out_path):
            return out_path

        if not url or not isinstance(url, str):
            return "./downloads/default.jpg"

        # if it's already a local path
        if os.path.isfile(url):
            return url

        # if requests not available, just return default (caller will use fallback)
        if requests is None:
            print("[thumbnail-download] requests not available, skipping download")
            return "./downloads/default.jpg"

        # Basic safety: accept http/https only
        if not (url.startswith("http://") or url.startswith("https://")):
            return "./downloads/default.jpg"

        # stream download (small image)
        r = requests.get(url, timeout=8, stream=True)
        if r.status_code == 200:
            with open(out_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if not chunk:
                        break
                    f.write(chunk)
            # verify saved
            if os.path.isfile(out_path):
                return out_path
        else:
            print(f"[thumbnail-download] HTTP {r.status_code} for {url}")
    except Exception as e:
        print(f"[thumbnail-download] error downloading {url}: {e}")
    return "./downloads/default.jpg"


# ------------------------------
# Thumbnail Generator (safe)
# ------------------------------
def safe_generate_thumbnail(vidid: str,
                            title: str = "Unknown",
                            artist: str = "Unknown",
                            provider_thumb: Optional[str] = None) -> str:
    """
    Generate a thumbnail synchronously and return the file path.
    Flow:
      1) If provider_thumb is a URL -> attempt to download it into ./downloads/{vidid}.jpg
      2) Use local ./downloads/{vidid}.jpg (if exists) as album_art_path to produce card via get_thumb()
      3) If generation fails, fallback to provider_thumb (URL) or configured images or local default
    """
    try:
        os.makedirs("./thumbnails", exist_ok=True)
    except Exception:
        pass

    # Step 1: ensure we have a local album_art_path
    album_art_path = f"./downloads/{vidid}.jpg"
    # If provider provided and is remote URL, try download (will return default path on failure)
    if provider_thumb and isinstance(provider_thumb, str) and (provider_thumb.startswith("http://") or provider_thumb.startswith("https://")):
        try:
            dl_path = download_provider_thumbnail(provider_thumb, vidid)
            if dl_path and os.path.isfile(dl_path):
                album_art_path = dl_path
        except Exception as e:
            print(f"[safe_generate_thumbnail] download failed: {e}")

    # If provider_thumb is local path and exists, use it
    if provider_thumb and isinstance(provider_thumb, str) and os.path.isfile(provider_thumb):
        album_art_path = provider_thumb

    # If local album_art_path missing, fall back to local default (downloads/default.jpg)
    if not os.path.isfile(album_art_path):
        if os.path.isfile("./downloads/default.jpg"):
            album_art_path = "./downloads/default.jpg"
        else:
            # ensure downloads exists and create a tiny default if not present
            try:
                os.makedirs("./downloads", exist_ok=True)
                from PIL import Image
                tiny = "./downloads/default.jpg"
                if not os.path.isfile(tiny):
                    Image.new("RGB", (640, 360), (44, 9, 8)).save(tiny)
                album_art_path = tiny
            except Exception:
                album_art_path = "./downloads/default.jpg"

    # Step 2: call your generator (get_thumb)
    output_path = f"./thumbnails/{vidid}.png"
    try:
        # get_thumb signature in your thumbnails.py:
        # get_thumb(album_art_path, song_title=..., artist_name=..., output_path=..., style="A", reference_image=None)
        ret = get_thumb(
            album_art_path,
            song_title=title,
            artist_name=artist,
            output_path=output_path,
            style="A"
        )
        # Some implementations may return the path, others may not
        if isinstance(ret, str) and os.path.isfile(ret):
            return ret
        if os.path.isfile(output_path):
            return output_path
    except Exception as e:
        print(f"[safe_generate_thumbnail] get_thumb() failed: {e}")

    # Step 3: fallback chain (try provider_thumb first)
    if provider_thumb:
        try:
            if os.path.isfile(provider_thumb):
                return provider_thumb
            if provider_thumb.startswith("http://") or provider_thumb.startswith("https://"):
                return provider_thumb
        except Exception:
            pass

    # Step 4: try configured images in config
    for candidate in (
        getattr(config, "TELEGRAM_AUDIO_URL", None),
        getattr(config, "SOUNCLOUD_IMG_URL", None),
        getattr(config, "STREAM_IMG_URL", None),
        getattr(config, "TELEGRAM_VIDEO_URL", None),
        getattr(config, "SUPPORT_CHAT", None),
    ):
        if not candidate:
            continue
        if isinstance(candidate, str) and os.path.isfile(candidate):
            return candidate
        if isinstance(candidate, str) and (candidate.startswith("http://") or candidate.startswith("https://")):
            return candidate

    # Step 5: local downloads/default.jpg
    if os.path.isfile("./downloads/default.jpg"):
        return "./downloads/default.jpg"

    # Step 6: create minimal fallback thumbnail
    try:
        from PIL import Image
        tiny_path = "./thumbnails/fallback_default.png"
        if not os.path.isfile(tiny_path):
            Image.new("RGB", (640, 360), (44, 9, 8)).save(tiny_path)
        return tiny_path
    except Exception as e:
        print(f"[safe_generate_thumbnail] final fallback failed: {e}")
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

                # generate thumbnail (download provider thumb when available)
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
        thumbnail = result.get("thumb")  # provider thumbnail (url or path)
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

            # create/send thumbnail
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
                try:
                    if thumbnail and thumbnail != img:
                        run = await app.send_photo(
                            original_chat_id,
                            photo=thumbnail,
                            caption=_["stream_1"].format(
                                f"https://t.me/{app.username}?start=info_{vidid}",
                                title[:23], duration_min, user_name
                            ),
                            reply_markup=InlineKeyboardMarkup(button)
                        )
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
            # use configured soundcloud image (URL) or generated fallback
            img_to_send = getattr(config, "SOUNCLOUD_IMG_URL", None) or safe_generate_thumbnail("sc_" + str(randint(10000, 99999)), title, user_name)
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
    # Telegram (uploaded audio/video)
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