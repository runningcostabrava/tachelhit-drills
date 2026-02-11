import os
import sys
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Try to import moviepy components
MOVIEPY_AVAILABLE = False
try:
    from moviepy.video.VideoClip import ImageClip
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.video.compositing.concatenate import concatenate_videoclips
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    print(f"[SHORTS] MoviePy import error: {e}")
    # Check if it's a missing dependency
    if "ffmpeg" in str(e).lower():
        print("[SHORTS] FFmpeg may not be installed. On Render, add 'imageio-ffmpeg' to requirements.txt")
    MOVIEPY_AVAILABLE = False

SHORTS_DIR = "media/shorts"
os.makedirs(SHORTS_DIR, exist_ok=True)

# YouTube Shorts dimensions (9:16 aspect ratio)
SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920

def check_moviepy():
    """Helper to check if moviepy is available and raise informative error."""
    if not MOVIEPY_AVAILABLE:
        raise ImportError(
            "MoviePy not available. Please install: pip install moviepy imageio-ffmpeg opencv-python-headless\n"
            "If on Render, ensure these are in requirements.txt."
        )

def generate_youtube_short(drill_data, output_filename):
    """
    Generate a YouTube Short video from drill data
    """
    check_moviepy()
    
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

    try:
        video_clip.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac' if audio_clip else None,
            preset='medium',
            logger=None  # Suppress verbose output
        )
    except Exception as e:
        # Clean up before raising
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
        video_clip.close()
        if audio_clip:
            audio_clip.close()
        raise RuntimeError(f"Failed to write video file: {e}")

    # Clean up
    video_clip.close()
    if audio_clip:
        audio_clip.close()
    if os.path.exists(temp_img_path):
        os.remove(temp_img_path)

    print(f"[SHORTS] Short generated successfully: {output_path}")
    return output_path

def generate_drillplayer_demo(test_id, drills_data, output_filename):
    """
    Generate a demo video of the Drill Player for a test.
    Shows each drill with its text and simulates the player interface.
    """
    check_moviepy()
    
    print(f"[DEMO] Generating Drill Player demo for test {test_id}")

    # Dimensions for desktop simulation (16:9 aspect ratio)
    DEMO_WIDTH = 1280
    DEMO_HEIGHT = 720

    # Create a list of video clips for each drill
    clips = []
    
    for i, drill in enumerate(drills_data):
        print(f"[DEMO] Processing drill {i+1}/{len(drills_data)}: {drill.get('text_catalan', 'No text')[:30]}...")
        
        # Create background simulating a browser window
        bg = Image.new('RGB', (DEMO_WIDTH, DEMO_HEIGHT), color=(240, 242, 245))
        draw = ImageDraw.Draw(bg)
        
        # Try to load fonts
        try:
            font_title = ImageFont.truetype("arialbd.ttf", 28)
            font_header = ImageFont.truetype("arialbd.ttf", 22)
            font_text = ImageFont.truetype("arial.ttf", 20)
            font_small = ImageFont.truetype("arial.ttf", 16)
        except:
            font_title = ImageFont.load_default()
            font_header = ImageFont.load_default()
            font_text = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw browser header
        draw.rectangle([0, 0, DEMO_WIDTH, 60], fill=(50, 50, 60))
        draw.text((20, 20), "Tachelhit Drill Player - Test Demo", fill=(255, 255, 255), font=font_title)
        
        # Draw drill counter
        counter_text = f"Drill {i+1} of {len(drills_data)}"
        counter_bbox = draw.textbbox((0, 0), counter_text, font=font_header)
        counter_width = counter_bbox[2] - counter_bbox[0]
        draw.text((DEMO_WIDTH - counter_width - 30, 20), counter_text, fill=(200, 200, 200), font=font_header)
        
        # Main content area
        content_top = 80
        content_height = DEMO_HEIGHT - content_top - 100
        draw.rectangle([40, content_top, DEMO_WIDTH - 40, content_top + content_height], 
                      fill=(255, 255, 255), outline=(200, 200, 200), width=2)
        
        # Drill image (if available)
        img_x = 60
        img_y = content_top + 30
        if drill.get('image_url'):
            try:
                image_path = f"media/{drill['image_url'].replace('/media/', '')}"
                if os.path.exists(image_path):
                    drill_img = Image.open(image_path)
                    # Resize to fit
                    max_size = (300, 200)
                    drill_img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    if drill_img.mode == 'RGBA':
                        drill_img = drill_img.convert('RGB')
                    bg.paste(drill_img, (img_x, img_y))
                    # Draw image border
                    draw.rectangle([img_x-2, img_y-2, img_x+drill_img.width+2, img_y+drill_img.height+2], 
                                  outline=(100, 100, 100), width=1)
            except Exception as e:
                print(f"[DEMO] Error loading image: {e}")
        
        # Text area
        text_x = img_x + 320 if drill.get('image_url') else img_x
        text_y = img_y
        
        # Catalan text
        if drill.get('text_catalan'):
            draw.text((text_x, text_y), "Català:", fill=(0, 100, 200), font=font_header)
            draw.text((text_x, text_y + 30), drill['text_catalan'], fill=(0, 0, 0), font=font_text)
        
        # Tachelhit text
        if drill.get('text_tachelhit'):
            draw.text((text_x, text_y + 80), "Tachelhit:", fill=(0, 150, 0), font=font_header)
            draw.text((text_x, text_y + 110), drill['text_tachelhit'], fill=(0, 0, 0), font=font_text)
        
        # Arabic text
        if drill.get('text_arabic'):
            draw.text((text_x, text_y + 160), "العربية:", fill=(150, 0, 150), font=font_header)
            # Arabic text is right-aligned
            arabic_text = drill['text_arabic']
            arabic_bbox = draw.textbbox((0, 0), arabic_text, font=font_text)
            arabic_width = arabic_bbox[2] - arabic_bbox[0]
            draw.text((text_x + 200 - arabic_width, text_y + 190), arabic_text, fill=(0, 0, 0), font=font_text)
        
        # Simulate player controls at bottom
        controls_y = content_top + content_height + 20
        draw.rectangle([40, controls_y, DEMO_WIDTH - 40, controls_y + 60], 
                      fill=(248, 249, 250), outline=(200, 200, 200), width=1)
        
        # Play button
        draw.rectangle([60, controls_y + 10, 150, controls_y + 50], fill=(76, 175, 80), outline=(56, 155, 60), width=2)
        draw.text((85, controls_y + 20), "▶ PLAY", fill=(255, 255, 255), font=font_header)
        
        # TTS button
        draw.rectangle([170, controls_y + 10, 300, controls_y + 50], fill=(156, 39, 176), outline=(136, 19, 156), width=2)
        draw.text((190, controls_y + 20), "🗣 TTS", fill=(255, 255, 255), font=font_header)
        
        # Navigation buttons
        draw.rectangle([DEMO_WIDTH - 300, controls_y + 10, DEMO_WIDTH - 200, controls_y + 50], 
                      fill=(33, 150, 243), outline=(13, 130, 223), width=2)
        draw.text((DEMO_WIDTH - 280, controls_y + 20), "← PREV", fill=(255, 255, 255), font=font_header)
        
        draw.rectangle([DEMO_WIDTH - 180, controls_y + 10, DEMO_WIDTH - 80, controls_y + 50], 
                      fill=(33, 150, 243), outline=(13, 130, 223), width=2)
        draw.text((DEMO_WIDTH - 160, controls_y + 20), "NEXT →", fill=(255, 255, 255), font=font_header)
        
        # Convert image to numpy array and create clip
        img_array = np.array(bg)
        # Each drill appears for 5 seconds
        clip = ImageClip(img_array, duration=5.0)
        
        # Add audio TTS if available (using audio_tts_url)
        if drill.get('audio_tts_url'):
            try:
                audio_path = f"media/{drill['audio_tts_url'].replace('/media/', '')}"
                if os.path.exists(audio_path):
                    audio_clip = AudioFileClip(audio_path)
                    # Ensure clip duration matches audio length
                    clip = clip.with_duration(max(5.0, audio_clip.duration + 1.0))
                    clip = clip.with_audio(audio_clip)
            except Exception as e:
                print(f"[DEMO] Error loading TTS audio: {e}")
        
        clips.append(clip)
    
    if not clips:
        raise Exception("No drills to generate demo video")
    
    # Concatenate all clips
    final_clip = concatenate_videoclips(clips, method="compose")
    
    # Add intro title
    intro_bg = Image.new('RGB', (DEMO_WIDTH, DEMO_HEIGHT), color=(30, 30, 50))
    intro_draw = ImageDraw.Draw(intro_bg)
    try:
        font_big = ImageFont.truetype("arialbd.ttf", 48)
        font_medium = ImageFont.truetype("arial.ttf", 24)
    except:
        font_big = ImageFont.load_default()
        font_medium = ImageFont.load_default()
    
    intro_draw.text((DEMO_WIDTH//2 - 200, DEMO_HEIGHT//2 - 60), "Drill Player Demo", fill=(255, 255, 255), font=font_big)
    intro_draw.text((DEMO_WIDTH//2 - 150, DEMO_HEIGHT//2 + 20), f"Test ID: {test_id} - {len(drills_data)} drills", 
                   fill=(200, 200, 200), font=font_medium)
    intro_array = np.array(intro_bg)
    intro_clip = ImageClip(intro_array, duration=3.0)
    
    # Add outro
    outro_bg = Image.new('RGB', (DEMO_WIDTH, DEMO_HEIGHT), color=(30, 30, 50))
    outro_draw = ImageDraw.Draw(outro_bg)
    outro_draw.text((DEMO_WIDTH//2 - 150, DEMO_HEIGHT//2 - 30), "Demo Completed", fill=(255, 255, 255), font=font_big)
    outro_draw.text((DEMO_WIDTH//2 - 120, DEMO_HEIGHT//2 + 40), "tachelhit-drills.vercel.app", 
                   fill=(200, 200, 200), font=font_medium)
    outro_array = np.array(outro_bg)
    outro_clip = ImageClip(outro_array, duration=3.0)
    
    # Combine intro, main content, outro
    final_clip = concatenate_videoclips([intro_clip, final_clip, outro_clip], method="compose")
    
    # Write video file
    output_path = os.path.join(SHORTS_DIR, output_filename)
    print(f"[DEMO] Writing demo video to: {output_path}")
    
    try:
        final_clip.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            logger=None
        )
    finally:
        # Clean up
        final_clip.close()
        intro_clip.close()
        outro_clip.close()
    
    print(f"[DEMO] Demo video generated successfully: {output_path}")
    return output_path
