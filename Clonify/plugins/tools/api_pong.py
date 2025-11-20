import time
import psutil
import requests
from pyrogram import filters
from Clonify import app


@app.on_callback_query(filters.regex("api_pong"))
async def api_pong(client, query):

    start = time.time()

    # ── PING CHECK ──────────────────────────────────────────────
    try:
        requests.get("https://google.com", timeout=5)
        ping = round((time.time() - start) * 1000, 2)
        api_ping = f"{ping} ms"
    except:
        api_ping = "FAILED"

    # ── CPU / RAM ───────────────────────────────────────────────
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent

    # ── SERVER STATUS ───────────────────────────────────────────
    server_status = "ᴏɴʟɪɴᴇ" if cpu < 90 else "ᴏᴠᴇʀʟᴏᴀᴅ"

    text = f"""
💗 ɴᴇxᴀ ᴍᴜsɪᴄ — sʏsᴛᴇᴍ sᴛᴀᴛᴜs

• ᴀᴘɪ ᴘɪɴɢ: {api_ping}
• ᴄᴘᴜ ᴜsᴀɢᴇ: {cpu}%
• ʀᴀᴍ ᴜsᴀɢᴇ: {ram}%
• sᴇʀᴠᴇʀ: {server_status}

 ʏᴀʏᴀ!! ᴇᴠᴇʀʏᴛʜɪɴɢ ɪs ғɪɴᴇ...
"""

    await query.answer(text, show_alert=True)