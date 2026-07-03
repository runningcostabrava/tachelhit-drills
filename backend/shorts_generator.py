import os
import requests
import traceback
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# --- 1. Robust MoviePy Import ---
try:
    # Try setting ffmpeg path manually if available (helps on some Linux envs)
    import imageio_ffmpeg
    os.environ["FFMPEG_BINARY"] = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    pass # rely on system ffmpeg

from moviepy.video.VideoClip import ImageClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy import concatenate_videoclips
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip

# --- Configuration ---
SHORTS_DIR = "media/shorts"
os.makedirs(SHORTS_DIR, exist_ok=True)

# --- Helper Functions ---

def download_file(url, folder):
    """
    Downloads a file from a Cloudinary URL to a local folder.
    Returns the local path or None if failed.
    """
    if not url or not isinstance(url, str) or not url.startswith("http"):
        return None

    try:
        # Create a unique filename to avoid collisions
        clean_name = url.split("/")[-1].split("?")[0]
        # Use timestamp to ensure uniqueness
        local_filename = f"dl_{int(datetime.now().timestamp())}_{clean_name}"
        local_path = os.path.join(folder, local_filename)

        print(f"[FETCH] Downloading: {url}")
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_path
    except Exception as e:
        print(f"[FETCH] Failed to download {url}: {e}")
        return None

def get_safe_font():
    """
    Returns a default font object that is guaranteed to work on Linux.
    """
    try:
        # Try to load a nicer font if you uploaded one (optional)
        # return ImageFont.truetype("arial.ttf", 60)
        return ImageFont.load_default()
    except:
        return ImageFont.load_default()

# --- Main Generators ---

def generate_youtube_short(drill_data, output_filename):
    """
    Generates a single vertical video (9:16) for a drill.
    """
    print(f"[SHORTS] Processing drill: {drill_data.get('text_catalan', 'Unknown')}")

    # 1. Download Assets
    img_path = download_file(drill_data.get('image_url'), SHORTS_DIR)
    audio_path = download_file(drill_data.get('audio_url'), SHORTS_DIR)

    temp_files = [img_path, audio_path] # Keep track for cleanup

    # 2. Setup Canvas (Vertical 9:16)
    W, H = 1080, 1920
    bg_color = (30, 30, 50)
    bg = Image.new('RGB', (W, H), color=bg_color)
    draw = ImageDraw.Draw(bg)

    # 3. Add Background Image
    if img_path and os.path.exists(img_path):
        try:
            overlay = Image.open(img_path).convert('RGB')
            # Resize to cover roughly half the screen width
            overlay.thumbnail((W, H//2), Image.Resampling.LANCZOS)

            # Center the image
            x_pos = (W - overlay.width) // 2
            y_pos = (H - overlay.height) // 2
            bg.paste(overlay, (x_pos, y_pos))
        except Exception as e:
            print(f"[IMG] Error processing image: {e}")

    # 4. Add Text (Catalan)
    try:
        font = get_safe_font()
        text = drill_data.get('text_catalan', '')
        if text:
            # Basic centering logic for default font
            # (Default font doesn't support getting text size well in older Pillow, so we just place it)
            draw.text((100, 200), text, fill="white", font=font)
    except Exception as e:
        print(f"[TEXT] Error drawing text: {e}")

    # 5. Create Video Clip
    img_array = np.array(bg)

    # 6. Handle Audio & Duration
    audio_clip = None
    duration = 5.0 # Default duration if no audio

    if audio_path and os.path.exists(audio_path):
        try:
            audio_clip = AudioFileClip(audio_path)
            duration = audio_clip.duration
        except Exception as e:
            print(f"[AUDIO] Error loading audio file: {e}")

    # Create the video clip
    # CRITICAL FIX: Set duration exactly to what we decided (the audio length)
    video_clip = ImageClip(img_array).with_duration(duration)

    if audio_clip:
        # Attach audio. video_clip duration matches audio_clip duration exactly now.
        video_clip = video_clip.with_audio(audio_clip)

    # 7. Write Output
    final_path = os.path.join(SHORTS_DIR, output_filename)

    try:
        # Use 'medium' preset for speed, 24fps is standard for simple animation
        video_clip.write_videofile(
            final_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            logger=None  # Suppress generic progress bars to keep logs clean
        )
    except Exception as e:
        print(f"[WRITE] MoviePy Write Error: {e}")
        raise RuntimeError(f"Failed to render video: {e}")
    finally:
        # 8. Cleanup Resources
        # Close MoviePy objects to release file locks
        try:
            video_clip.close()
            if audio_clip:
                audio_clip.close()
        except:
            pass

        # Delete temp downloaded files to save space
        for f in temp_files:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

    return final_path

def generate_drillplayer_demo(test_id, drills_data, output_filename):
    """
    Generates a sequential demo video combining multiple drills.
    """
    print(f"[DEMO] Starting demo for Test {test_id} with {len(drills_data)} drills")
    clips = []
    generated_files = [] # Track temp videos to delete them later

    try:
        for i, drill in enumerate(drills_data):
            # Generate a temporary short for this specific drill
            temp_filename = f"temp_demo_{test_id}_{i}_{int(datetime.now().timestamp())}.mp4"

            try:
                # Generate the single clip
                path = generate_youtube_short(drill, temp_filename)
                generated_files.append(path)

                # Load it back as a VideoFileClip
                # We assume the previous function succeeded if it returned a path
                clip = VideoFileClip(path)
                clips.append(clip)
            except Exception as e:
                print(f"[DEMO] Skipped drill {drill.get('id')} due to error: {e}")
                # Continue to next drill instead of failing the whole test
                continue

        if not clips:
            raise RuntimeError("No valid clips were generated for this demo test.")

        # Concatenate all valid clips
        print(f"[DEMO] Concatenating {len(clips)} clips...")
        final_clip = concatenate_videoclips(clips, method="compose")

        final_path = os.path.join(SHORTS_DIR, output_filename)

        final_clip.write_videofile(
            final_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            logger=None
        )

        # Close the final composite clip
        final_clip.close()
        return final_path

    except Exception as e:
        print(f"[DEMO] Critical Error: {e}")
        raise e
    finally:
        # Cleanup: Close all loaded clips and delete temp video files
        for clip in clips:
            try:
                clip.close()
            except:
                pass

        for f in generated_files:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass