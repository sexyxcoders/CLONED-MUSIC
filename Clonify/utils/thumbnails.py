from typing import Optional, Union
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os

# ==========================================
# EXACT DIMENSIONS FROM SCREENSHOT
# ==========================================
CANVAS_WIDTH = 1500
CANVAS_HEIGHT = 800
WIDGET_WIDTH = 1450
WIDGET_HEIGHT = 650
WIDGET_X = 25
WIDGET_Y = 75
CORNER_RADIUS = 70
ALBUM_ART_WIDTH = 630
ALBUM_ART_HEIGHT = 650

# ==========================================
# EXACT COLORS (sampled from screenshot)
# ==========================================
BG_COLOR = (87, 26, 20)              # outer background
WIDGET_BG = (44, 9, 8)               # card background
ALBUM_TINT = (180, 0, 0)             # red overlay on album art
TEXT_TITLE = (255, 255, 255)         # "Salvatore" - pure white
TEXT_ARTIST = (215, 205, 200)        # "Lana Del Rey" - light gray
TEXT_LABEL = (238, 220, 214)         # "Airdopes 131" - cream
PROGRESS_BG = (95, 38, 34)           # progress bar background
PROGRESS_FG = (255, 192, 182)        # progress bar fill
ICON_COLOR = (255, 255, 255)         # buttons/icons white
VOLUME_BG = (95, 38, 34)
VOLUME_FG = (255, 192, 182)

# ==========================================
# FONT FALLBACKS
# ==========================================
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "C:\\Windows\\Fonts\\arial.ttf",
    "./fonts/DejaVuSans-Bold.ttf",
]

def get_font(size, bold=False):
    for path in FONT_PATHS:
        try:
            if os.path.isfile(path):
                return ImageFont.truetype(path, size)
        except:
            pass
    return ImageFont.load_default()

# ==========================================
# UTILITIES
# ==========================================
def rounded_rectangle_mask(size, radius):
    """Create rounded rectangle mask."""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0]-1, size[1]-1), radius=radius, fill=255)
    return mask

def apply_red_tint(img, tint_color=ALBUM_TINT, strength=0.65):
    """Apply red color overlay to image."""
    overlay = Image.new("RGB", img.size, tint_color)
    return Image.blend(img.convert("RGB"), overlay, strength)

def seconds_to_mmss(seconds):
    """Convert seconds to MM:SS format."""
    s = max(0, int(seconds))
    return f"{s // 60}:{s % 60:02d}"

def load_album_art(path):
    """Load and validate album art."""
    if path is None:
        return create_placeholder()
    if isinstance(path, str) and os.path.isfile(path):
        try:
            return Image.open(path).convert("RGB")
        except:
            return create_placeholder()
    if isinstance(path, Image.Image):
        return path.convert("RGB")
    return create_placeholder()

def create_placeholder():
    """Create gradient placeholder."""
    img = Image.new("RGB", (ALBUM_ART_WIDTH, ALBUM_ART_HEIGHT), (30, 10, 10))
    draw = ImageDraw.Draw(img)
    for y in range(ALBUM_ART_HEIGHT):
        ratio = y / max(1, ALBUM_ART_HEIGHT - 1)
        r = int(30 + (200 - 30) * ratio)
        draw.line((0, y, ALBUM_ART_WIDTH, y), fill=(r, 8, 8))
    return img

# ==========================================
# ICON DRAWING FUNCTIONS
# ==========================================
def draw_play_button(draw, x, y, size=1.0, color=ICON_COLOR):
    """Draw play triangle."""
    scale = int(24 * size)
    draw.polygon([
        (x - scale, y - scale),
        (x - scale, y + scale),
        (x + scale, y)
    ], fill=color)

def draw_pause_button(draw, x, y, size=1.0, color=ICON_COLOR):
    """Draw pause bars."""
    h = int(28 * size)
    w = int(8 * size)
    gap = int(6 * size)
    # Left bar
    draw.rectangle((x - w - gap, y - h, x - gap, y + h), fill=color)
    # Right bar
    draw.rectangle((x + gap, y - h, x + w + gap, y + h), fill=color)

def draw_skip_back(draw, x, y, size=1.0, color=ICON_COLOR):
    """Draw skip back (double bars)."""
    t = int(17 * size)
    # Vertical line
    draw.rectangle((x - t - 6, y - t, x - t - 2, y + t), fill=color)
    # Triangle
    draw.polygon([
        (x + t, y - t),
        (x + t, y + t),
        (x - 2, y)
    ], fill=color)

def draw_skip_next(draw, x, y, size=1.0, color=ICON_COLOR):
    """Draw skip next (double bars)."""
    t = int(17 * size)
    # Triangle
    draw.polygon([
        (x - t, y - t),
        (x - t, y + t),
        (x + 2, y)
    ], fill=color)
    # Vertical line
    draw.rectangle((x + t + 2, y - t, x + t + 6, y + t), fill=color)

def draw_speaker(draw, x, y, size=1.0, color=ICON_COLOR):
    """Draw speaker icon."""
    scale = int(10 * size)
    # Speaker cone
    draw.polygon([
        (x - scale, y - scale),
        (x - scale, y + scale),
        (x, y + scale),
        (x, y - scale)
    ], fill=color)
    # Speaker back
    draw.rectangle((x + 2, y - scale // 2, x + scale // 2, y + scale // 2), fill=color)

def draw_bluetooth(draw, x, y, size=1.0, color=ICON_COLOR):
    """Draw bluetooth symbol."""
    scale = int(12 * size)
    # Central line
    draw.line((x, y - scale, x, y + scale), fill=color, width=3)
    # Upper right diagonal
    draw.line((x, y - scale, x + scale, y), fill=color, width=3)
    # Lower right diagonal
    draw.line((x, y + scale, x + scale, y), fill=color, width=3)

# ==========================================
# MAIN GENERATOR
# ==========================================
def generate_thumbnail(
    song_title="Salvatore",
    artist_name="Lana Del Rey",
    album_label="Airdopes 131",
    album_art_path=None,
    current_seconds=141,
    total_seconds=260,
    output_path="player_thumb.png"
):
    """Generate exact music player thumbnail."""

    # Create base canvas
    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), BG_COLOR)

    # Create rounded widget background
    widget = Image.new("RGB", (WIDGET_WIDTH, WIDGET_HEIGHT), WIDGET_BG)
    widget_mask = rounded_rectangle_mask((WIDGET_WIDTH, WIDGET_HEIGHT), CORNER_RADIUS)
    canvas.paste(widget, (WIDGET_X, WIDGET_Y), widget_mask)

    # Load and process album art
    album_art = load_album_art(album_art_path)
    album_art = ImageOps.fit(album_art, (ALBUM_ART_WIDTH, ALBUM_ART_HEIGHT), Image.Resampling.LANCZOS)
    album_art = apply_red_tint(album_art, ALBUM_TINT, 0.65)

    # Apply rounded mask to album art
    art_mask = rounded_rectangle_mask((ALBUM_ART_WIDTH, ALBUM_ART_HEIGHT), 28)
    album_art = album_art.convert("RGBA")
    album_art.putalpha(art_mask)
    canvas.paste(album_art, (WIDGET_X, WIDGET_Y), album_art)

    # Start drawing on canvas
    draw = ImageDraw.Draw(canvas)

    # Load fonts - exact sizes from screenshot
    font_label = get_font(42)
    font_title = get_font(90)
    font_artist = get_font(50)
    font_time = get_font(34)

    # Text positioning
    text_x = WIDGET_X + ALBUM_ART_WIDTH + 70
    text_y = WIDGET_Y + 30

    # Draw album label (small text above title)
    draw.text((text_x, text_y), album_label, font=font_label, fill=TEXT_LABEL)
    text_y += 70

    # Draw song title
    title_text = song_title
    title_bbox = draw.textbbox((0, 0), title_text, font=font_title)
    title_width = title_bbox[2] - title_bbox[0]

    # Truncate if too long
    max_width = WIDGET_WIDTH - ALBUM_ART_WIDTH - 180
    if title_width > max_width:
        while len(title_text) > 3 and draw.textbbox((0, 0), title_text + "...", font=font_title)[2] > max_width:
            title_text = title_text[:-1]
        title_text += "..."

    draw.text((text_x, text_y), title_text, font=font_title, fill=TEXT_TITLE)
    text_y += 100

    # Draw artist name
    draw.text((text_x, text_y), artist_name, font=font_artist, fill=TEXT_ARTIST)
    text_y += 80

    # Progress bar
    bar_width = 620
    bar_height = 14
    bar_x = text_x
    bar_y = text_y

    # Background
    draw.rounded_rectangle(
        (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
        radius=10,
        fill=PROGRESS_BG
    )

    # Progress fill
    if total_seconds > 0:
        progress = current_seconds / total_seconds
        fill_width = int(bar_width * progress)
        draw.rounded_rectangle(
            (bar_x, bar_y, bar_x + fill_width, bar_y + bar_height),
            radius=10,
            fill=PROGRESS_FG
        )

    # Time labels
    time_y = bar_y + bar_height + 10
    current_str = seconds_to_mmss(current_seconds)
    remaining_str = "-" + seconds_to_mmss(total_seconds - current_seconds)

    draw.text((bar_x, time_y), current_str, font=font_time, fill=TEXT_ARTIST)
    draw.text((bar_x + bar_width - 120, time_y), remaining_str, font=font_time, fill=TEXT_ARTIST)

    # Control buttons
    button_y = WIDGET_Y + 330
    button_center_x = bar_x + bar_width // 2 - 60

    draw_skip_back(draw, button_center_x - 80, button_y, 1.0, ICON_COLOR)
    draw_pause_button(draw, button_center_x, button_y, 1.0, ICON_COLOR)
    draw_skip_next(draw, button_center_x + 80, button_y, 1.0, ICON_COLOR)

    # Speaker and bluetooth icons
    draw_speaker(draw, bar_x + bar_width + 60, button_y, 1.0, ICON_COLOR)
    draw_bluetooth(draw, bar_x + bar_width + 110, button_y, 0.8, ICON_COLOR)

    # Volume bar (bottom)
    volume_y = WIDGET_Y + WIDGET_HEIGHT - 120
    volume_width = 560
    volume_height = 14

    draw.rounded_rectangle(
        (bar_x, volume_y, bar_x + volume_width, volume_y + volume_height),
        radius=8,
        fill=VOLUME_BG
    )

    # Volume fill (approximately 72%)
    volume_level = int(volume_width * 0.72)
    draw.rounded_rectangle(
        (bar_x, volume_y, bar_x + volume_level, volume_y + volume_height),
        radius=8,
        fill=VOLUME_FG
    )

    # Volume slider endpoints
    draw.rectangle((bar_x - 14, volume_y + 2, bar_x - 6, volume_y + volume_height - 2), fill=ICON_COLOR)
    draw.rectangle((bar_x + volume_width + 6, volume_y + 2, bar_x + volume_width + 14, volume_y + volume_height - 2), fill=ICON_COLOR)

    # Save output
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    canvas.save(output_path, quality=95)
    print(f"✓ Thumbnail saved: {output_path}")
    return output_path

# ==========================================
# USAGE EXAMPLES
# ==========================================
if __name__ == "__main__":
    # Example 1: With no album art
    generate_thumbnail(
        song_title="Salvatore",
        artist_name="Lana Del Rey",
        album_label="Airdopes 131",
        current_seconds=141,
        total_seconds=260,
        output_path="player_default.png"
    )

    # Example 2: With custom album art (uncomment if you have an image)
    # generate_thumbnail(
    #     song_title="Salvatore",
    #     artist_name="Lana Del Rey",
    #     album_label="Airdopes 131",
    #     album_art_path="album_cover.jpg",
    #     current_seconds=141,
    #     total_seconds=260,
    #     output_path="player_with_art.png"
    # )