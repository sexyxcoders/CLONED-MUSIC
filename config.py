import os
import re
from os import getenv
from dotenv import load_dotenv
from pyrogram import filters

# ====================================================
# Load Environment Variables
# ====================================================
load_dotenv()

# ====================================================
# Basic Configuration
# ====================================================
API_ID = int(getenv("API_ID"))
API_HASH = getenv("API_HASH")

BOT_TOKEN = getenv("BOT_TOKEN")
BOT_ID = getenv("BOT_ID", "8588527575")

OWNER_ID = int(getenv("OWNER_ID", 7804917014))
OWNER_USERNAME = getenv("OWNER_USERNAME", "noncarder")

BOT_USERNAME = getenv("BOT_USERNAME", "NexaEraMusicBot")
BOT_NAME = getenv("BOT_NAME", "˹𝛆ℓ𝛊𝛎α ꭙ 𝐌𝛖𝛅𝛊𝛓˼")
ASSUSERNAME = getenv("ASSUSERNAME", "NexaAssistant")

# ====================================================
# Database and Logging
# ====================================================
MONGO_DB_URI = getenv("MONGO_DB_URI")
LOGGER_ID = int(getenv("LOGGER_ID"))
CLONE_LOGGER = LOGGER_ID

# ====================================================
# Heroku Configuration
# ====================================================
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")
HEROKU_API_KEY = getenv("HEROKU_API_KEY")

# ====================================================
# External APIs
# ====================================================
API_URL = getenv("API_URL", "https://api.thequickearn.xyz")  # YouTube audio API
VIDEO_API_URL = getenv("VIDEO_API_URL", "https://api.video.thequickearn.xyz")
API_KEY = getenv("API_KEY", "NxGBNexGenBots4e1026")

# ====================================================
# Git & Repository Settings
# ====================================================
SOURCE = getenv("SOURCE", "https://github.com/sexyxcoders")
UPSTREAM_REPO = getenv("UPSTREAM_REPO", "https://github.com/sexyxcoders/CLONED-MUSIC")
UPSTREAM_BRANCH = getenv("UPSTREAM_BRANCH", "main")
GIT_TOKEN = getenv("GIT_TOKEN", "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")

# ====================================================
# Support Links
# ====================================================
SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/NexaCoders")
SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/NexaMeetup")
CHAT = getenv("CHAT", "https://t.me/NexaMeetup")

# ====================================================
# Assistant Settings
# ====================================================
AUTO_LEAVING_ASSISTANT = getenv("AUTO_LEAVING_ASSISTANT", "False")
AUTO_LEAVE_ASSISTANT_TIME = int(getenv("ASSISTANT_LEAVE_TIME", "9000"))

# ====================================================
# Duration & Limits
# ====================================================
DURATION_LIMIT_MIN = int(getenv("DURATION_LIMIT", 17000))
SONG_DOWNLOAD_DURATION = int(getenv("SONG_DOWNLOAD_DURATION", "9999999"))
SONG_DOWNLOAD_DURATION_LIMIT = int(getenv("SONG_DOWNLOAD_DURATION_LIMIT", "9999999"))
PLAYLIST_FETCH_LIMIT = int(getenv("PLAYLIST_FETCH_LIMIT", 25))

TG_AUDIO_FILESIZE_LIMIT = int(getenv("TG_AUDIO_FILESIZE_LIMIT", "5242880000"))
TG_VIDEO_FILESIZE_LIMIT = int(getenv("TG_VIDEO_FILESIZE_LIMIT", "5242880000"))

# ====================================================
# Spotify Configuration
# ====================================================
SPOTIFY_CLIENT_ID = getenv("SPOTIFY_CLIENT_ID", "1c21247d714244ddbb09925dac565aed")
SPOTIFY_CLIENT_SECRET = getenv("SPOTIFY_CLIENT_SECRET", "709e1a2969664491b58200860623ef19")

# ====================================================
# Session Strings
# ====================================================
STRING1 = getenv("STRING_SESSION", "")
STRING2 = getenv("STRING_SESSION2", None)

# ====================================================
# User Filters & Runtime Caches
# ====================================================
BANNED_USERS = filters.user()
adminlist = {}
lyrical = {}
votemode = {}
autoclean = []
confirmer = {}

# ====================================================
# Image & Media URLs
# ====================================================
STREAMI_PICS = [
    "https://files.catbox.moe/jhucwc.mp4",
    "https://files.catbox.moe/znvojp.mp4",
]

START_IMG_URL = getenv("START_IMG_URL", "https://files.catbox.moe/zywku1.jpg")
HELP_IMG_URL = getenv("HELP_IMG_URL", "https://files.catbox.moe/ok8tat.mp4")
PING_IMG_URL = getenv("PING_IMG_URL", "https://files.catbox.moe/we2hw5.jpg")

PLAYLIST_IMG_URL = "https://files.catbox.moe/kh9h0n.jpg"
STATS_IMG_URL = "https://files.catbox.moe/jdwd10.jpg"
TELEGRAM_AUDIO_URL = "https://files.catbox.moe/kh9h0n.jpg"
TELEGRAM_VIDEO_URL = "https://i.ibb.co/gL3ykkyh/play-music.jpg"
STREAM_IMG_URL = "https://files.catbox.moe/kh9h0n.jpg"
SOUNCLOUD_IMG_URL = "https://files.catbox.moe/kh9h0n.jpg"
YOUTUBE_IMG_URL = "https://files.catbox.moe/kh9h0n.jpg"
SPOTIFY_ARTIST_IMG_URL = "https://files.catbox.moe/kh9h0n.jpg"
SPOTIFY_ALBUM_IMG_URL = "https://files.catbox.moe/kh9h0n.jpg"
SPOTIFY_PLAYLIST_IMG_URL = "https://files.catbox.moe/kh9h0n.jpg"

# ====================================================
# Duration Conversion
# ====================================================
def time_to_seconds(time: str) -> int:
    parts = list(map(int, time.split(":")))
    return sum(x * 60**i for i, x in enumerate(reversed(parts)))

DURATION_LIMIT = int(time_to_seconds(f"{DURATION_LIMIT_MIN}:00"))

# ====================================================
# Validation for URLs
# ====================================================
if SUPPORT_CHANNEL and not re.match(r"(?:http|https)://", SUPPORT_CHANNEL):
    raise SystemExit(
        "[ERROR] - Invalid SUPPORT_CHANNEL URL. It must start with https://"
    )

if SUPPORT_CHAT and not re.match(r"(?:http|https)://", SUPPORT_CHAT):
    raise SystemExit(
        "[ERROR] - Invalid SUPPORT_CHAT URL. It must start with https://"
    )

# ====================================================
# Emojis / Greetings
# ====================================================
GREET = [
    "💞", "🥂", "🔍", "🧪", "⚡️", "🔥", "🦋", "🎩", "🌈",
    "🍷", "🥃", "🥤", "🕊️", "💌", "🧨"
]

# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------
