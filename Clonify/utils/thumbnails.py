import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython import VideosSearch
from config import YOUTUBE_IMG_URL


def changeImageSize(maxWidth, maxHeight, image):
    w_ratio = maxWidth / image.size[0]
    h_ratio = maxHeight / image.size[1]
    new_w = int(image.size[0] * w_ratio)
    new_h = int(image.size[1] * h_ratio)
    return image.resize((new_w, new_h))


def truncate(text):
    words = text.split(" ")
    t1 = ""
    t2 = ""
    for w in words:
        if len(t1) + len(w) < 35:
            t1 += " " + w
        elif len(t2) + len(w) < 35:
            t2 += " " + w
    return [t1.strip(), t2.strip()]


async def get_thumb(videoid):

    final_path = f"cache/{videoid}_nexa.png"
    if os.path.exists(final_path):
        return final_path

    # Fetch Metadata
    url = f"https://www.youtube.com/watch?v={videoid}"
    results = VideosSearch(url, limit=1)
    data = (await results.next())["result"][0]

    title = re.sub("\W+", " ", data.get("title", "Unknown")).title()
    duration = data.get("duration", "Unknown")
    thumb_url = data["thumbnails"][0]["url"].split("?")[0]
    views = data.get("viewCount", {}).get("short", "Unknown")
    channel = data.get("channel", {}).get("name", "Unknown")

    # Download thumbnail
    async with aiohttp.ClientSession() as session:
        async with session.get(thumb_url) as resp:
            if resp.status == 200:
                async with aiofiles.open(f"cache/{videoid}.png", "wb") as f:
                    await f.write(await resp.read())

    yt = Image.open(f"cache/{videoid}.png")

    # ----- BACKGROUND BLUR -----
    bg = changeImageSize(1600, 900, yt).convert("RGBA")
    bg = bg.filter(ImageFilter.GaussianBlur(25))
    enhancer = ImageEnhance.Brightness(bg)
    bg = enhancer.enhance(0.45)

    # ----- MAIN CANVAS -----
    canvas = Image.new("RGBA", (1600, 900))
    canvas.paste(bg, (0, 0))

    draw = ImageDraw.Draw(canvas)

    # Fonts
    title_font = ImageFont.truetype("Clonify/assets/font3.ttf", 60)
    small_font = ImageFont.truetype("Clonify/assets/font.ttf", 35)
    mid_font = ImageFont.truetype("Clonify/assets/font2.ttf", 40)

    # ----- Main card -----
    card_w, card_h = 1150, 600
    card_x, card_y = 225, 90

    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 60))

    # neon border
    glow = Image.new("RGBA", (card_w, card_h))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.rounded_rectangle((0, 0, card_w, card_h), radius=40, outline=(160, 70, 255), width=8)
    glow = glow.filter(ImageFilter.GaussianBlur(15))

    canvas.paste(glow, (card_x, card_y), glow)
    canvas.paste(card, (card_x, card_y), card)

    # ----- Paste main thumbnail inside card -----
    main_thumb = yt.resize((500, 500))
    canvas.paste(main_thumb, (card_x + 40, card_y + 50))

    # ----- Title & details inside card -----
    t1, t2 = truncate(title)

    draw.text((card_x + 580, card_y + 100), t1, fill="white", font=title_font)
    draw.text((card_x + 580, card_y + 175), t2, fill="white", font=title_font)

    draw.text((card_x + 580, card_y + 260),
              f"YouTube : {views} | Time : {duration}",
              fill="white", font=small_font)

    draw.text((card_x + 580, card_y + 330),
              f"Player : @NexaEraMusicBot",
              fill="#bf65ff", font=mid_font)

    # ----- Watermark on top-right -----
    draw.text((1300, 40), "@nexameetup", fill="white", font=mid_font)

    # Save final
    canvas.save(final_path)

    os.remove(f"cache/{videoid}.png")

    return final_path