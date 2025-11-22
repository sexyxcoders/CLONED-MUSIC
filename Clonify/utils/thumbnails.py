from PIL import Image, ImageDraw, ImageFont
import os
from typing import Optional

class ThumbnailGenerator:
    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.margin = 40
        
    def create_gradient_background(self, color_start=(220, 50, 20), color_end=(80, 20, 10)):
        """Create a gradient background from top to bottom"""
        img = Image.new('RGB', (self.width, self.height))
        draw = ImageDraw.Draw(img)
        
        r_start, g_start, b_start = color_start
        r_end, g_end, b_end = color_end
        
        for y in range(self.height):
            ratio = y / self.height
            r = int(r_start + (r_end - r_start) * ratio)
            g = int(g_start + (g_end - g_start) * ratio)
            b = int(b_start + (b_end - b_start) * ratio)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        
        return img
    
    def resize_album_art(self, image_path, size=350):
        """Resize and return album art"""
        try:
            img = Image.open(image_path).convert('RGB')
            img.thumbnail((size, size), Image.Resampling.LANCZOS)
            return img
        except Exception as e:
            print(f"Error loading image: {e}")
            return None
    
    def round_corners(self, img, radius=30):
        """Add rounded corners to an image"""
        circle = Image.new('L', (radius * 2, radius * 2), 0)
        draw = ImageDraw.Draw(circle)
        draw.ellipse([0, 0, radius * 2, radius * 2], fill=255)
        
        alpha = Image.new('L', img.size, 255)
        w, h = img.size
        alpha.paste(circle.crop([0, 0, radius, radius]), [0, 0])
        alpha.paste(circle.crop([radius, 0, radius * 2, radius]), [w - radius, 0])
        alpha.paste(circle.crop([0, radius, radius, radius * 2]), [0, h - radius])
        alpha.paste(circle.crop([radius, radius, radius * 2, radius * 2]), [w - radius, h - radius])
        
        img.putalpha(alpha)
        return img
    
    def seconds_to_time(self, seconds: int) -> str:
        """Convert seconds to MM:SS format"""
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins}:{secs:02d}"
    
    def create_thumbnail(self, album_art_path: str, song_title: str, artist_name: str, 
                        album: str = "Airdopes 131", current_seconds: int = 141, 
                        total_seconds: int = 281, output_path: str = "thumbnail.png"):
        """
        Create a music player thumbnail
        
        Args:
            album_art_path: Path to album art image
            song_title: Song title
            artist_name: Artist name
            album: Album name (default: Airdopes 131)
            current_seconds: Current playback time in seconds (default: 141 = 2:21)
            total_seconds: Total duration in seconds (default: 281 = 4:41)
            output_path: Output file path
        """
        
        # Convert seconds to time strings
        current_time = self.seconds_to_time(current_seconds)
        duration = self.seconds_to_time(total_seconds)
        progress_ratio = current_seconds / total_seconds if total_seconds > 0 else 0
        
        # Create gradient background
        base_img = self.create_gradient_background()
        
        # Load and resize album art
        album_art = self.resize_album_art(album_art_path, size=350)
        if album_art:
            # Apply rounded corners to album art
            album_art = self.round_corners(album_art, radius=30)
            # Paste album art on the left
            base_img.paste(album_art, (self.margin, self.height // 2 - 175), album_art if album_art.mode == 'RGBA' else None)
        
        draw = ImageDraw.Draw(base_img)
        
        # Load fonts
        try:
            album_font = ImageFont.truetype("arial.ttf", 28)
            title_font = ImageFont.truetype("arial.ttf", 48)
            artist_font = ImageFont.truetype("arial.ttf", 32)
            time_font = ImageFont.truetype("arial.ttf", 24)
            control_font = ImageFont.truetype("arial.ttf", 40)
        except:
            album_font = ImageFont.load_default()
            title_font = ImageFont.load_default()
            artist_font = ImageFont.load_default()
            time_font = ImageFont.load_default()
            control_font = ImageFont.load_default()
        
        # Right side content
        right_x = 450 + self.margin
        right_y = 120
        
        # Draw album info
        draw.text((right_x, right_y), album, font=album_font, fill=(200, 150, 120))
        
        # Draw song title
        right_y += 50
        draw.text((right_x, right_y), song_title, font=title_font, fill=(255, 255, 255))
        
        # Draw artist name
        right_y += 70
        draw.text((right_x, right_y), artist_name, font=artist_font, fill=(200, 200, 200))
        
        # Draw progress bar
        right_y += 80
        bar_width = 600
        bar_height = 8
        bar_x = right_x
        bar_y = right_y
        
        # Background bar
        draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], 
                       fill=(80, 50, 40), outline=(150, 100, 80))
        
        # Progress based on current time
        draw.rectangle([bar_x, bar_y, bar_x + bar_width * progress_ratio, bar_y + bar_height], 
                       fill=(255, 100, 50))
        
        # Draw times
        right_y += 25
        draw.text((right_x, right_y), current_time, font=time_font, fill=(200, 200, 200))
        draw.text((right_x + bar_width - 60, right_y), f"-{duration}", font=time_font, fill=(200, 200, 200))
        
        # Draw playback controls
        control_y = right_y + 80
        control_spacing = 80
        
        # Previous, Play/Pause, Next, Volume buttons (simplified as text)
        controls = ["⏮", "⏸", "⏭", "🔊"]
        for i, control in enumerate(controls):
            draw.text((right_x + i * control_spacing + 100, control_y), control, 
                     font=control_font, fill=(255, 255, 255))
        
        # Draw volume bar
        volume_bar_x = right_x + 20
        volume_bar_y = control_y + 100
        volume_bar_width = 500
        volume_bar_height = 6
        
        draw.rectangle([volume_bar_x, volume_bar_y, volume_bar_x + volume_bar_width, 
                       volume_bar_y + volume_bar_height], fill=(80, 50, 40))
        draw.rectangle([volume_bar_x, volume_bar_y, volume_bar_x + volume_bar_width * 0.7, 
                       volume_bar_y + volume_bar_height], fill=(255, 100, 50))
        
        # Save thumbnail
        base_img.save(output_path, quality=95)
        print(f"Thumbnail saved to {output_path}")
        
        return output_path


# Usage Example
if __name__ == "__main__":
    generator = ThumbnailGenerator(width=1280, height=720)
    
    # Create thumbnail with time in seconds
    # Example: 2:21 (141 seconds) out of 4:41 (281 seconds)
    generator.create_thumbnail(
        album_art_path="album_art.png",  # Path to your album art image
        song_title="Salvatore",
        artist_name="Lana Del Rey",
        album="Airdopes 131",
        current_seconds=141,  # 2:21
        total_seconds=281,    # 4:41
        output_path="thumbnail.png"
    )
    
    # More examples:
    # generator.create_thumbnail(
    #     album_art_path="album.png",
    #     song_title="Another Song",
    #     artist_name="Some Artist",
    #     current_seconds=45,    # 0:45
    #     total_seconds=240,     # 4:00
    #     output_path="thumbnail2.png"
    # )