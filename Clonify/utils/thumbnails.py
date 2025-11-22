"""
music_player_thumbnail_b.py
Generates a pixel-accurate 'Full Album Photo Player' thumbnail (Style B).

Usage example:
    from music_player_thumbnail_b import get_thumb
    get_thumb(
        album_art_path="cover.jpg",        # supply your album art path
        song_title="Salvatore",
        artist_name="Lana Del Rey",
        album_label="Airdopes 131",
        current_seconds=141,
        total_seconds=260,
        output_path="out_b.png"
    )
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import os, math

# -------------------- Config --------------------
CANVAS = (1280, 720)
WIDGET = (1100, 500)        # width,height of the rounded card
WIDGET_POS = (90, 110)      # top-left of the widget on canvas
ART_SIZE = (430, 500)       # left album area size
RADIUS = 55                 # corner radius for widget and art
BG_COLOR = (86, 20, 18)     # page background
WIDGET_COLOR = (44, 10, 10) # inner widget color (slightly lighter/darker)
RED_TINT = (170, 0, 0)      # red overlay for album art
ALBUM_COLOR = (220, 190, 165)
TITLE_COLOR = (255, 255, 255)
ARTIST_COLOR = (215, 205, 200)
PROG_BG = (95, 38, 34)
PROG_FG = (255, 200, 192)
ICON_COLOR = (255, 255, 255)
# -------------------------------------------------

def load_font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "./fonts/DejaVuSans.ttf",
        "./fonts/Arial.ttf"
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def rounded_mask(size, r):
    w,h = size
    m = Image.new("L",(w,h),0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0,0,w,h), radius=r, fill=255)
    return m

def tint_image(img, tint=RED_TINT, strength=0.66):
    red = Image.new("RGB", img.size, tint)
    return Image.blend(img.convert("RGB"), red, strength)

def placeholder_art(size):
    w,h = size
    img = Image.new("RGB", (w,h), (40,10,10))
    draw = ImageDraw.Draw(img)
    # vertical gradient
    for y in range(h):
        t = y/h
        r = int(30 + (200-30)*t)
        g = int(10 + (10-10)*(1-t))
        b = int(10 + (20-10)*(1-t))
        draw.line((0,y,w,y), fill=(r,g,b))
    # rounded vignette
    vign = Image.new("L",(w,h),0)
    dv = ImageDraw.Draw(vign)
    dv.ellipse((-int(w*0.1), -int(h*0.2), int(w*1.1), int(h*1.2)), fill=180)
    vign = vign.filter(ImageFilter.GaussianBlur(60))
    img.putalpha(255)
    red = Image.new("RGBA", img.size, (255,0,0,40))
    img = Image.alpha_composite(img.convert("RGBA"), red).convert("RGB")
    return img

def mmss(sec):
    s = max(0,int(sec))
    return f"{s//60}:{s%60:02d}"

def draw_controls(draw, cx, cy):
    """Draw prev, pause, next, and speaker icon centered around (cx,cy)."""
    # prev (double triangle left)
    t = 34
    gap = 12
    left_x = cx - 220
    y = cy
    # first left triangle
    draw.polygon([(left_x, y+t),(left_x+t, y+t/2),(left_x, y)], fill=ICON_COLOR)
    # second left triangle (offset)
    draw.polygon([(left_x+t+8, y+t),(left_x+t*2+8, y+t/2),(left_x+t+8, y)], fill=ICON_COLOR)

    # pause (two rects)
    px = cx - 30
    draw.rectangle((px-22, y-28, px-6, y+28), fill=ICON_COLOR)
    draw.rectangle((px+6, y-28, px+22, y+28), fill=ICON_COLOR)

    # next (double triangle right)
    nx = cx + 120
    draw.polygon([(nx, y),(nx+t, y+t/2),(nx, y+t)], fill=ICON_COLOR)
    draw.polygon([(nx+t+8, y),(nx+t*2+8, y+t/2),(nx+t+8, y+t)], fill=ICON_COLOR)

    # speaker (right-most)
    spx = cx + 300
    spy = y - 22
    # speaker box
    draw.polygon([(spx, spy+18),(spx+22, spy),(spx+22, spy+44),(spx, spy+26)], fill=ICON_COLOR)
    # waves (3 arcs approximated by lines)
    draw.arc((spx+26, spy-8, spx+66, spy+52), -60, 60, fill=ICON_COLOR, width=3)
    draw.arc((spx+34, spy-2, spx+86, spy+58), -60, 60, fill=ICON_COLOR, width=3)
    draw.arc((spx+42, spy+6, spx+104, spy+66), -60, 60, fill=ICON_COLOR, width=3)

def create_thumbnail(
    album_art_path,
    song_title="Unknown Title",
    artist_name="Unknown Artist",
    album_label="Airdopes 131",
    current_seconds=141,
    total_seconds=260,
    output_path="player_b.png",
    canvas_size=CANVAS
):
    cw,ch = canvas_size
    canvas = Image.new("RGB",(cw,ch), BG_COLOR)

    # Widget base
    widget = Image.new("RGB", WIDGET, WIDGET_COLOR)
    # subtle inner shadow
    shadow = Image.new("RGBA", WIDGET, (0,0,0,0))
    ds = ImageDraw.Draw(shadow)
    for i in range(10):
        a = int(12 + i*5)
        ds.rounded_rectangle((i,i,WIDGET[0]-i,WIDGET[1]-i), radius=RADIUS, fill=(0,0,0,a))
    widget = Image.alpha_composite(widget.convert("RGBA"), shadow).convert("RGB")

    # paste rounded widget on canvas
    widget_mask = rounded_mask(WIDGET, RADIUS)
    canvas.paste(widget, WIDGET_POS, widget_mask)

    # Album art area
    ax,ay = WIDGET_POS
    # Try to load provided art, otherwise generate placeholder
    if album_art_path and os.path.isfile(album_art_path):
        art = Image.open(album_art_path).convert("RGB")
        art = ImageOps.fit(art, ART_SIZE, method=Image.Resampling.LANCZOS, centering=(0.5,0.5))
    else:
        art = placeholder_art(ART_SIZE)

    # Tint art red and round corners
    art = tint_image(art, strength=0.7)
    art_rgba = art.convert("RGBA")
    art_mask = rounded_mask(ART_SIZE, RADIUS)
    art_rgba.putalpha(art_mask)
    canvas.paste(art_rgba, (ax,ay), art_rgba)

    # Right-side content (texts, bars, controls)
    draw = ImageDraw.Draw(canvas)
    # fonts
    f_album = load_font(30)
    f_title = load_font(72, bold=True)
    f_artist = load_font(44)
    f_time = load_font(28)

    right_x = ax + ART_SIZE[0] + 60
    cy = ay + 20

    # album label
    draw.text((right_x, cy), album_label, font=f_album, fill=ALBUM_COLOR)
    cy += 58

    # title (truncate elegantly if too long)
    max_w = WIDGET[0] - ART_SIZE[0] - 140
    title = song_title
    # truncate using textlength
    while draw.textlength(title, font=f_title) > max_w and len(title) > 4:
        title = title[:-2]
    if title != song_title:
        title = title[:-3] + "..."
    draw.text((right_x, cy), title, font=f_title, fill=TITLE_COLOR)
    cy += 96

    # artist
    draw.text((right_x, cy), artist_name, font=f_artist, fill=ARTIST_COLOR)
    cy += 80

    # progress bar
    bar_w = 520
    bar_h = 12
    bx = right_x
    by = cy
    draw.rounded_rectangle((bx,by,bx+bar_w,by+bar_h), radius=8, fill=PROG_BG)
    progress = 0.0
    if total_seconds > 0:
        progress = max(0.0, min(1.0, float(current_seconds)/float(total_seconds)))
    fg = int(bar_w * progress)
    if fg > 0:
        draw.rounded_rectangle((bx,by,bx+fg,by+bar_h), radius=8, fill=PROG_FG)
    cy += 30

    # times
    draw.text((bx, cy), mmss(current_seconds), font=f_time, fill=ARTIST_COLOR)
    draw.text((bx + bar_w - 80, cy), "-" + mmss(total_seconds), font=f_time, fill=ARTIST_COLOR)
    cy += 70

    # controls (center area)
    controls_center_x = bx + 120
    controls_center_y = cy
    draw_controls(draw, controls_center_x, controls_center_y)

    # bottom volume bar inside widget
    vol_y = WIDGET_POS[1] + WIDGET[1] - 100
    vol_x = right_x
    vol_w = 480
    vol_h = 12
    draw.rounded_rectangle((vol_x, vol_y, vol_x+vol_w, vol_y+vol_h), radius=8, fill=PROG_BG)
    vol_level = int(vol_w * 0.72)
    draw.rounded_rectangle((vol_x, vol_y, vol_x+vol_level, vol_y+vol_h), radius=8, fill=PROG_FG)
    # small squares at ends like screenshot
    draw.rectangle((vol_x - 10, vol_y+2, vol_x - 4, vol_y+vol_h-2), fill=ICON_COLOR)
    draw.rectangle((vol_x + vol_w + 6, vol_y+2, vol_x + vol_w + 12, vol_y+vol_h-2), fill=ICON_COLOR)

    # subtle stroke around widget for crisp edges
    stroke = Image.new("RGBA", WIDGET, (0,0,0,0))
    sd = ImageDraw.Draw(stroke)
    sd.rounded_rectangle((1,1,WIDGET[0]-2,WIDGET[1]-2), radius=RADIUS-2, outline=(20,8,8,80), width=2)
    canvas.paste(stroke, WIDGET_POS, stroke)

    # Save
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    canvas.save(output_path, quality=95)
    print("[music_player_thumbnail_b] Saved:", output_path)
    return output_path

# Backwards-compatible wrapper
def get_thumb(album_art_path,
              song_title="Unknown Title",
              artist_name="Unknown Artist",
              album_label="Airdopes 131",
              current_seconds=141,
              total_seconds=260,
              output_path="player_b_out.png",
              canvas_size=CANVAS):
    return create_thumbnail(
        album_art_path=album_art_path,
        song_title=song_title,
        artist_name=artist_name,
        album_label=album_label,
        current_seconds=current_seconds,
        total_seconds=total_seconds,
        output_path=output_path,
        canvas_size=canvas_size
    )

# Quick demo when run as script
if __name__ == "__main__":
    test_art = "album.jpg"  # replace with your image file, or leave absent to test placeholder
    if not os.path.isfile(test_art):
        test_art = None
    get_thumb(
        album_art_path=test_art,
        song_title="Salvatore",
        artist_name="Lana Del Rey",
        album_label="Airdopes 131",
        current_seconds=141,
        total_seconds=260,
        output_path="player_b_demo.png"
    )