import os from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

#--------------------------- CONFIG ---------------------------

CANVAS = (1280, 720) RADIUS = 55 BG_COLOR = (86, 20, 18) WIDGET_COLOR = (44, 10, 10) RED_TINT = (170, 0, 0) TITLE_COLOR = (255, 255, 255) ARTIST_COLOR = (215, 205, 200) ALBUM_COLOR = (220, 190, 165) PROG_BG = (95, 38, 34) PROG_FG = (255, 200, 192) ICON_COLOR = (255, 255, 255)

#--------------------------- HELPERS ---------------------------

def load_font(size, bold=False): paths = [ "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "./fonts/DejaVuSans.ttf", "./fonts/Arial.ttf", ] for p in paths: if os.path.isfile(p): try: return ImageFont.truetype(p, size) except: pass return ImageFont.load_default()

def rounded_mask(size, radius): mask = Image.new("L", size, 0) d = ImageDraw.Draw(mask) d.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255) return mask

def tint(img, color=RED_TINT, strength=0.7): overlay = Image.new("RGB", img.size, color) return Image.blend(img, overlay, strength)

def mmss(sec): sec = max(0, int(sec)) return f"{sec//60}:{sec%60:02d}"

#--------------------------- CORE RENDER ---------------------------

def render_style_b( album_art, song_title, artist_name, album_label, current_seconds, total_seconds, output, ): canvas = Image.new("RGB", CANVAS, BG_COLOR)

# Widget
W = (1100, 500)
W_POS = (90, 110)

widget = Image.new("RGB", W, WIDGET_COLOR)
mask = rounded_mask(W, RADIUS)
canvas.paste(widget, W_POS, mask)

# Art area
ART = (430, 500)
art = ImageOps.fit(album_art, ART, Image.Resampling.LANCZOS)
art = tint(art)

art_rgba = art.convert("RGBA")
art_rgba.putalpha(rounded_mask(ART, RADIUS))
canvas.paste(art_rgba, W_POS, art_rgba)

draw = ImageDraw.Draw(canvas)

# Fonts
f_album = load_font(30)
f_title = load_font(72)
f_artist = load_font(44)
f_time = load_font(28)

right_x = W_POS[0] + ART[0] + 60
cy = W_POS[1] + 20

draw.text((right_x, cy), album_label, fill=ALBUM_COLOR, font=f_album)
cy += 60

max_w = W[0] - ART[0] - 140
title = song_title
while draw.textlength(title, font=f_title) > max_w and len(title) > 4:
    title = title[:-2]
if title != song_title:
    title = title[:-3] + "..."
draw.text((right_x, cy), title, fill=TITLE_COLOR, font=f_title)
cy += 100

draw.text((right_x, cy), artist_name, fill=ARTIST_COLOR, font=f_artist)
cy += 80

# Progress bar
bar_w = 520
bar_h = 12
bx = right_x
by = cy

draw.rounded_rectangle((bx, by, bx + bar_w, by + bar_h), radius=8, fill=PROG_BG)

progress = max(0, min(1, current_seconds / max(total_seconds, 1)))
fg = int(bar_w * progress)
if fg:
    draw.rounded_rectangle((bx, by, bx + fg, by + bar_h), radius=8, fill=PROG_FG)

cy += 30
draw.text((bx, cy), mmss(current_seconds), font=f_time, fill=ARTIST_COLOR)
draw.text((bx + bar_w - 80, cy), "-" + mmss(total_seconds), font=f_time, fill=ARTIST_COLOR)

canvas.save(output, quality=95)
return output

#--------------------------- PUBLIC API ---------------------------

def generate_thumbnail( style="B", album_art_path=None, song_title="Unknown Title", artist_name="Unknown Artist", album_label="Airdopes 131", current_seconds=0, total_seconds=200, output_path="thumbnail.png", ): if album_art_path and os.path.isfile(album_art_path): img = Image.open(album_art_path).convert("RGB") else: img = Image.new("RGB", (430, 500), (80, 20, 20))

style = style.upper()

if style == "B":
    return render_style_b(
        img,
        song_title,
        artist_name,
        album_label,
        current_seconds,
        total_seconds,
        output_path,
    )

raise ValueError(f"Unknown thumbnail style: {style}")

Backwards compatibility

def get_thumb( album_art_path, song_title="Unknown Title", artist_name="Unknown Artist", album_label="Airdopes 131", current_seconds=0, total_seconds=200, output_path="thumbnail.png", style="B", ): return generate_thumbnail( style=style, album_art_path=album_art_path, song_title=song_title, artist_name=artist_name, album_label=album_label, current_seconds=current_seconds, total_seconds=total_seconds, output_path=output_path, )