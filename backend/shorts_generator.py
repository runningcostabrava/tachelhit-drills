import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import numpy as np

try:
    from moviepy.video.VideoClip import ImageClip
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.video.compositing.concatenate import concatenate_videoclips
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    print(f"MoviePy not fully available: {e}")
    MOVIEPY_AVAILABLE = False

SHORTS_DIR = "media/shorts"
os.makedirs(SHORTS_DIR, exist_ok=True)

# YouTube Shorts dimensions (9:16 aspect ratio)
SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920

def generate_youtube_short(drill_data, output_filename):
    """
    Generate a YouTube Short video from drill data
    """
    if not MOVIEPY_AVAILABLE:
        raise Exception("MoviePy not available. Please install: pip install moviepy")

    print(f"[SHORTS] Generating short: {output_filename}")

    # Create background image with text overlay
    img = Image.new('RGB', (SHORT_WIDTH, SHORT_HEIGHT), color=(30, 30, 50))
    draw = ImageDraw.Draw(img)

    # Load fonts
    try:
        font_large_bold = ImageFont.truetype("arialbd.ttf", 70)
        font_medium = ImageFont.truetype("arial.ttf", 50)
    except:
        font_large_bold = ImageFont.load_default()
        font_medium = ImageFont.load_default()

    # Add drill image if available (centered)
    if drill_data.get('image_url'):
        try:
            image_path = f"media/{drill_data['image_url'].replace('/media/', '')}"
            if os.path.exists(image_path):
                print(f"[SHORTS] Loading image: {image_path}")
                drill_img = Image.open(image_path)

                # Resize to fit in middle section
                max_size = (SHORT_WIDTH - 200, SHORT_HEIGHT - 800)
                drill_img.thumbnail(max_size, Image.Resampling.LANCZOS)

                # Convert RGBA to RGB if needed
                if drill_img.mode == 'RGBA':
                    drill_img = drill_img.convert('RGB')

                # Paste centered
                x = (SHORT_WIDTH - drill_img.width) // 2
                y = (SHORT_HEIGHT - drill_img.height) // 2
                img.paste(drill_img, (x, y))
        except Exception as e:
            print(f"[SHORTS] Error loading image: {e}")

    # Draw text overlays
    # Top: Catalan (bold, white)
    if drill_data.get('text_catalan'):
        text = drill_data['text_catalan']
        bbox = draw.textbbox((0, 0), text, font=font_large_bold)
        text_width = bbox[2] - bbox[0]
        x = (SHORT_WIDTH - text_width) // 2
        # Draw background rectangle
        draw.rectangle([x-20, 100, x+text_width+20, 200], fill=(0, 0, 0))
        draw.text((x, 120), text, fill=(255, 255, 255), font=font_large_bold)

    # Top-middle: Arabic (medium, gray)
    if drill_data.get('text_arabic'):
        text = drill_data['text_arabic']
        bbox = draw.textbbox((0, 0), text, font=font_medium)
        text_width = bbox[2] - bbox[0]
        x = (SHORT_WIDTH - text_width) // 2
        draw.rectangle([x-15, 230, x+text_width+15, 310], fill=(0, 0, 0))
        draw.text((x, 240), text, fill=(200, 200, 200), font=font_medium)

    # Bottom: Tachelhit (bold, gold)
    if drill_data.get('text_tachelhit'):
        text = drill_data['text_tachelhit']
        bbox = draw.textbbox((0, 0), text, font=font_large_bold)
        text_width = bbox[2] - bbox[0]
        x = (SHORT_WIDTH - text_width) // 2
        y = SHORT_HEIGHT - 200
        draw.rectangle([x-20, y-20, x+text_width+20, y+80], fill=(0, 0, 0))
        draw.text((x, y), text, fill=(255, 215, 0), font=font_large_bold)

    # Save temporary image
    temp_img_path = os.path.join(SHORTS_DIR, f"temp_{output_filename}.png")
    img.save(temp_img_path)

    # Create video from image
    img_array = np.array(img)
    duration = 4  # 4 seconds default

    # If there's audio, adjust duration
    audio_clip = None
    if drill_data.get('audio_url'):
        try:
            audio_path = f"media/{drill_data['audio_url'].replace('/media/', '')}"
            if os.path.exists(audio_path):
                print(f"[SHORTS] Adding audio: {audio_path}")
                audio_clip = AudioFileClip(audio_path)
                duration = max(duration, audio_clip.duration + 0.5)
        except Exception as e:
            print(f"[SHORTS] Error loading audio: {e}")

    # Create video clip
    video_clip = ImageClip(img_array, duration=duration)

    # Add audio if available
    if audio_clip:
        video_clip = video_clip.with_audio(audio_clip)

    # Write final video
    output_path = os.path.join(SHORTS_DIR, output_filename)
    print(f"[SHORTS] Writing video to: {output_path}")

    video_clip.write_videofile(
        output_path,
        fps=24,
        codec='libx264',
        audio_codec='aac' if audio_clip else None,
        preset='medium',
        logger=None  # Suppress verbose output
    )

    # Clean up
    video_clip.close()
    if audio_clip:
        audio_clip.close()
    if os.path.exists(temp_img_path):
        os.remove(temp_img_path)

    print(f"[SHORTS] Short generated successfully: {output_path}")
    return output_path
