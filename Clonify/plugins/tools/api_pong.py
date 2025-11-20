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
    server_status = "🟢 ᴏɴʟɪɴᴇ" if cpu < 90 else "🔴 ᴏᴠᴇʀʟᴏᴀᴅ"

    text = f"""
<b>💗 Nᴇxᴀ Mᴜsɪᴄ — Sʏsᴛᴇᴍ Sᴛᴀᴛᴜs</b>

• <b>ᴀᴘɪ ᴘɪɴɢ:</b> {api_ping}
• <b>ᴄᴘᴜ ᴜsᴀɢᴇ:</b> {cpu}%
• <b>ʀᴀᴍ ᴜsᴀɢᴇ:</b> {ram}%
• <b>sᴇʀᴠᴇʀ:</b> {server_status}

<b>✔ ʏᴀʏᴀ !! ᴇᴠᴇʀʏᴛʜɪɴɢ ɪs ғɪɴᴇ...</b>
"""

    await query.answer(text, show_alert=True)