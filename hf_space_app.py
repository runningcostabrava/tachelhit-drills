import os
import sys
import tempfile
import shutil
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import requests
import json # Import json for parsing drill_data strings

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Cloudinary
import cloudinary
import cloudinary.uploader
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# Try to import moviepy components and configure ffmpeg
MOVIEPY_AVAILABLE = False
MOVIEPY_ERROR = None

try:
    import imageio_ffmpeg
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    if ffmpeg_path:
        os.environ["FFMPEG_BINARY"] = ffmpeg_path
        print(f"[SHORTS] Found ffmpeg at: {ffmpeg_path}")
    else:
        print("[SHORTS] imageio-ffmpeg did not return a valid ffmpeg path")
except Exception as e:
    print(f"[SHORTS] Could not configure ffmpeg via imageio-ffmpeg: {e}")

try:
    from moviepy.video.VideoClip import ImageClip
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.video.compositing.concatenate import concatenate_videoclips
    import moviepy.config

    if 'FFMPEG_BINARY' in os.environ:
        moviepy.config.FFMPEG_BINARY = os.environ["FFMPEG_BINARY"]
        print(f"[SHORTS] Set moviepy FFMPEG_BINARY to: {moviepy.config.FFMPEG_BINARY}")
    else:
        import shutil
        ffmpeg_detected = shutil.which('ffmpeg')
        if ffmpeg_detected:
            moviepy.config.FFMPEG_BINARY = ffmpeg_detected
            print(f"[SHORTS] Auto-detected ffmpeg at: {ffmpeg_detected}")
        else:
            print("[SHORTS] No ffmpeg found in PATH")
    
    MOVIEPY_AVAILABLE = True
    print("[SHORTS] MoviePy imported successfully")
except ImportError as e:
    MOVIEPY_ERROR = str(e)
    print(f"[SHORTS] MoviePy import error: {e}")
    MOVIEPY_AVAILABLE = False
except Exception as e:
    MOVIEPY_ERROR = str(e)
    print(f"[SHORTS] Other error during MoviePy setup: {e}")
    MOVIEPY_AVAILABLE = False

SHORTS_DIR = "shorts_output" # Use a separate directory for outputs in HF Space
os.makedirs(SHORTS_DIR, exist_ok=True)
MEDIA_ROOT = "media" # Define MEDIA_ROOT for TTS function, though it downloads directly

# YouTube Shorts dimensions (9:16 aspect ratio)
SHORT_WIDTH = 1080
SHORT_HEIGHT = 1920

def check_moviepy():
    if not MOVIEPY_AVAILABLE:
        missing_msg = "MoviePy not available. "
        if MOVIEPY_ERROR:
            missing_msg += f"Error: {MOVIEPY_ERROR}. "
        missing_msg += "Please install: pip install moviepy imageio-ffmpeg opencv-python-headless
"
        missing_msg += "If on Render, ensure these are in requirements.txt and ffmpeg is installed (apt-get install ffmpeg)."
        raise ImportError(missing_msg)

# TTS function (moved from main.py)
def generate_catalan_tts(text: str, drill_id: int) -> str:
    """
    Generate Catalan TTS audio file and return the URL path.
    """
    try:
        from gtts import gTTS
        
        tts = gTTS(text=text, lang='ca', slow=False)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            temp_path = tmp.name
            tts.save(temp_path)
        
        timestamp = int(datetime.utcnow().timestamp())
        filename = f"tts_{drill_id}_{timestamp}.mp3"
        
        use_cloudinary = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))
        
        if use_cloudinary:
            result = cloudinary.uploader.upload(
                temp_path,
                folder="tachelhit/tts",
                public_id=f"tts_{drill_id}_{timestamp}",
                resource_type="video"
            )
            url = result['secure_url']
        else:
            # Fallback for local storage, though in HF Space Cloudinary should be used
            local_tts_dir = os.path.join(MEDIA_ROOT, "tts")
            os.makedirs(local_tts_dir, exist_ok=True)
            local_path = os.path.join(local_tts_dir, filename)
            shutil.move(temp_path, local_path)
            url = f"/media/tts/{filename}"
        
        if os.path.exists(temp_path):
            os.unlink(temp_path)
            
        return url
    except Exception as e:
        print(f"[TTS] Error generating TTS: {e}")
        raise

def generate_youtube_short_hf(drill_id: int, drill_data_str: str, output_filename: str) -> str:
    check_moviepy()
    drill_data = json.loads(drill_data_str) # Parse JSON string

    print(f"[SHORTS] Generating short: {output_filename}")

    img = Image.new('RGB', (SHORT_WIDTH, SHORT_HEIGHT), color=(30, 30, 50))
    draw = ImageDraw.Draw(img)

    try:
        font_large_bold = ImageFont.truetype("arialbd.ttf", 70)
        font_medium = ImageFont.truetype("arial.ttf", 50)
    except:
        font_large_bold = ImageFont.load_default()
        font_medium = ImageFont.load_default()

    if drill_data.get('image_url'):
        try:
            response = requests.get(drill_data['image_url'], stream=True)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_img:
                shutil.copyfileobj(response.raw, tmp_img)
                image_path = tmp_img.name

            drill_img = Image.open(image_path)
            max_size = (SHORT_WIDTH - 200, SHORT_HEIGHT - 800)
            drill_img.thumbnail(max_size, Image.Resampling.LANCZOS)
            if drill_img.mode == 'RGBA':
                drill_img = drill_img.convert('RGB')
            x = (SHORT_WIDTH - drill_img.width) // 2
            y = (SHORT_HEIGHT - drill_img.height) // 2
            img.paste(drill_img, (x, y))
            os.unlink(image_path)
        except Exception as e:
            print(f"[SHORTS] Error loading or processing image: {e}")

    if drill_data.get('text_catalan'):
        text = drill_data['text_catalan']
        bbox = draw.textbbox((0, 0), text, font=font_large_bold)
        text_width = bbox[2] - bbox[0]
        x = (SHORT_WIDTH - text_width) // 2
        draw.rectangle([x-20, 100, x+text_width+20, 200], fill=(0, 0, 0))
        draw.text((x, 120), text, fill=(255, 255, 255), font=font_large_bold)

    if drill_data.get('text_arabic'):
        text = drill_data['text_arabic']
        bbox = draw.textbbox((0, 0), text, font=font_medium)
        text_width = bbox[2] - bbox[0]
        x = (SHORT_WIDTH - text_width) // 2
        draw.rectangle([x-15, 230, x+text_width+15, 310], fill=(0, 0, 0))
        draw.text((x, 240), text, fill=(200, 200, 200), font=font_medium)

    if drill_data.get('text_tachelhit'):
        text = drill_data['text_tachelhit']
        bbox = draw.textbbox((0, 0), text, font=font_large_bold)
        text_width = bbox[2] - bbox[0]
        x = (SHORT_WIDTH - text_width) // 2
        y = SHORT_HEIGHT - 200
        draw.rectangle([x-20, y-20, x+text_width+20, y+80], fill=(0, 0, 0))
        draw.text((x, y), text, fill=(255, 215, 0), font=font_large_bold)

    temp_img_path = os.path.join(SHORTS_DIR, f"temp_{output_filename}.png")
    img.save(temp_img_path)

    img_array = np.array(img)
    duration = 4

    audio_clip = None
    if drill_data.get('audio_url'):
        try:
            response = requests.get(drill_data['audio_url'], stream=True)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_audio:
                shutil.copyfileobj(response.raw, tmp_audio)
                audio_path = tmp_audio.name
            
            print(f"[SHORTS] Adding audio: {audio_path}")
            audio_clip = AudioFileClip(audio_path)
            duration = max(duration, audio_clip.duration + 0.5)
            os.unlink(audio_path)
        except Exception as e:
            print(f"[SHORTS] Error loading audio: {e}")

    video_clip = ImageClip(img_array, duration=duration)

    if audio_clip:
        video_clip = video_clip.with_audio(audio_clip)

    output_path_local = os.path.join(SHORTS_DIR, output_filename)
    print(f"[SHORTS] Writing video to: {output_path_local}")

    try:
        video_clip.write_videofile(
            output_path_local,
            fps=24,
            codec='libx264',
            audio_codec='aac' if audio_clip else None,
            preset='medium',
            logger=None
        )
    except Exception as e:
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
        video_clip.close()
        if audio_clip:
            audio_clip.close()
        raise RuntimeError(f"Failed to write video file: {e}")

    video_clip.close()
    if audio_clip:
        audio_clip.close()
    if os.path.exists(temp_img_path):
        os.remove(temp_img_path)

    use_cloudinary = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))
    if use_cloudinary:
        print(f"[SHORTS] Uploading to Cloudinary")
        result = cloudinary.uploader.upload(
            output_path_local,
            folder="tachelhit/shorts",
            public_id=os.path.splitext(output_filename)[0],
            resource_type="video"
        )
        os.unlink(output_path_local)
        return result['secure_url']
    else:
        return output_path_local # Return local path for testing

def generate_drillplayer_demo_hf(test_id: int, drills_data_str: str, output_filename: str) -> str:
    check_moviepy()
    drills_data = json.loads(drills_data_str) # Parse JSON string
    
    print(f"[DEMO] Generating Drill Player demo for test {test_id}")

    DEMO_WIDTH = 1280
    DEMO_HEIGHT = 720

    clips = []
    
    for i, drill in enumerate(drills_data):
        print(f"[DEMO] Processing drill {i+1}/{len(drills_data)}: {drill.get('text_catalan', 'No text')[:30]}...")
        
        bg = Image.new('RGB', (DEMO_WIDTH, DEMO_HEIGHT), color=(240, 242, 245))
        draw = ImageDraw.Draw(bg)
        
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
        
        draw.rectangle([0, 0, DEMO_WIDTH, 60], fill=(50, 50, 60))
        draw.text((20, 20), "Tachelhit Drill Player - Test Demo", fill=(255, 255, 255), font=font_title)
        
        counter_text = f"Drill {i+1} of {len(drills_data)}"
        counter_bbox = draw.textbbox((0, 0), counter_text, font=font_header)
        counter_width = counter_bbox[2] - counter_bbox[0]
        draw.text((DEMO_WIDTH - counter_width - 30, 20), counter_text, fill=(200, 200, 200), font=font_header)
        
        content_top = 80
        content_height = DEMO_HEIGHT - content_top - 100
        draw.rectangle([40, content_top, DEMO_WIDTH - 40, content_top + content_height], 
                      fill=(255, 255, 255), outline=(200, 200, 200), width=2)
        
        img_x = 60
        img_y = content_top + 30
        if drill.get('image_url'):
            try:
                response = requests.get(drill['image_url'], stream=True)
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_img:
                    shutil.copyfileobj(response.raw, tmp_img)
                    image_path = tmp_img.name

                drill_img = Image.open(image_path)
                max_size = (300, 200)
                drill_img.thumbnail(max_size, Image.Resampling.LANCZOS)
                if drill_img.mode == 'RGBA':
                    drill_img = drill_img.convert('RGB')
                bg.paste(drill_img, (img_x, img_y))
                draw.rectangle([img_x-2, img_y-2, img_x+drill_img.width+2, img_y+drill_img.height+2], 
                              outline=(100, 100, 100), width=1)
                os.unlink(image_path)
            except Exception as e:
                print(f"[DEMO] Error loading image: {e}")
        
        text_x = img_x + 320 if drill.get('image_url') else img_x
        text_y = img_y
        
        if drill.get('text_catalan'):
            draw.text((text_x, text_y), "Català:", fill=(0, 100, 200), font=font_header)
            draw.text((text_x, text_y + 30), drill['text_catalan'], fill=(0, 0, 0), font=font_text)
        
        if drill.get('text_tachelhit'):
            draw.text((text_x, text_y + 80), "Tachelhit:", fill=(0, 150, 0), font=font_header)
            draw.text((text_x, text_y + 110), drill['text_tachelhit'], fill=(0, 0, 0), font=font_text)
        
        if drill.get('text_arabic'):
            draw.text((text_x, text_y + 160), "العربية:", fill=(150, 0, 150), font=font_header)
            arabic_text = drill['text_arabic']
            arabic_bbox = draw.textbbox((0, 0), arabic_text, font=font_text)
            arabic_width = arabic_bbox[2] - arabic_bbox[0]
            draw.text((text_x + 200 - arabic_width, text_y + 190), arabic_text, fill=(0, 0, 0), font=font_text)
        
        controls_y = content_top + content_height + 20
        draw.rectangle([40, controls_y, DEMO_WIDTH - 40, controls_y + 60], 
                      fill=(248, 249, 250), outline=(200, 200, 200), width=1)
        
        draw.rectangle([60, controls_y + 10, 150, controls_y + 50], fill=(76, 175, 80), outline=(56, 155, 60), width=2)
        draw.text((85, controls_y + 20), "▶ PLAY", fill=(255, 255, 255), font=font_header)
        
        draw.rectangle([170, controls_y + 10, 300, controls_y + 50], fill=(156, 39, 176), outline=(136, 19, 156), width=2)
        draw.text((190, controls_y + 20), "🗣 TTS", fill=(255, 255, 255), font=font_header)
        
        draw.rectangle([DEMO_WIDTH - 300, controls_y + 10, DEMO_WIDTH - 200, controls_y + 50], 
                      fill=(33, 150, 243), outline=(13, 130, 223), width=2)
        draw.text((DEMO_WIDTH - 280, controls_y + 20), "← PREV", fill=(255, 255, 255), font=font_header)
        
        draw.rectangle([DEMO_WIDTH - 180, controls_y + 10, DEMO_WIDTH - 80, controls_y + 50], 
                      fill=(33, 150, 243), outline=(13, 130, 223), width=2)
        draw.text((DEMO_WIDTH - 160, controls_y + 20), "NEXT →", fill=(255, 255, 255), font=font_header)
        
        img_array = np.array(bg)
        clip = ImageClip(img_array, duration=5.0)
        
        if drill.get('audio_tts_url'):
            try:
                response = requests.get(drill['audio_tts_url'], stream=True)
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_audio:
                    shutil.copyfileobj(response.raw, tmp_audio)
                    audio_path = tmp_audio.name
                
                audio_clip = AudioFileClip(audio_path)
                clip = clip.with_duration(max(5.0, audio_clip.duration + 1.0))
                clip = clip.with_audio(audio_clip)
                os.unlink(audio_path)
            except Exception as e:
                print(f"[DEMO] Error loading TTS audio: {e}")
        
        clips.append(clip)
    
    if not clips:
        raise Exception("No drills to generate demo video")
    
    final_clip = concatenate_videoclips(clips, method="compose")
    
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
    
    outro_bg = Image.new('RGB', (DEMO_WIDTH, DEMO_HEIGHT), color=(30, 30, 50))
    outro_draw = ImageDraw.Draw(outro_bg)
    outro_draw.text((DEMO_WIDTH//2 - 150, DEMO_HEIGHT//2 - 30), "Demo Completed", fill=(255, 255, 255), font=font_big)
    outro_draw.text((DEMO_WIDTH//2 - 120, DEMO_HEIGHT//2 + 40), "tachelhit-drills.vercel.app", 
                   fill=(200, 200, 200), font=font_medium)
    outro_array = np.array(outro_bg)
    outro_clip = ImageClip(outro_array, duration=3.0)
    
    final_clip = concatenate_videoclips([intro_clip, final_clip, outro_clip], method="compose")
    
    output_path_local = os.path.join(SHORTS_DIR, output_filename)
    print(f"[DEMO] Writing demo video to: {output_path_local}")
    
    try:
        final_clip.write_videofile(
            output_path_local,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            preset='medium',
            logger=None
        )
    finally:
        final_clip.close()
        intro_clip.close()
        outro_clip.close()
    
    use_cloudinary = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))
    if use_cloudinary:
        print(f"[DEMO] Uploading to Cloudinary")
        result = cloudinary.uploader.upload(
            output_path_local,
            folder="tachelhit/shorts",
            public_id=os.path.splitext(output_filename)[0],
            resource_type="video"
        )
        os.unlink(output_path_local)
        return result['secure_url']
    else:
        return output_path_local

import gradio as gr

def generate_video_api(
    video_type: str,
    drill_id: int = None,
    test_id: int = None,
    drill_data_str: str = None, # JSON string for single drill
    drills_data_str: str = None, # JSON string for list of drills
    output_filename: str = None
):
    try:
        if video_type == "short":
            if drill_id is None or drill_data_str is None or output_filename is None:
                raise ValueError("Missing parameters for 'short' video type.")
            result_url = generate_youtube_short_hf(drill_id, drill_data_str, output_filename)
            return {"video_path": result_url}
        elif video_type == "demo":
            if test_id is None or drills_data_str is None or output_filename is None:
                raise ValueError("Missing parameters for 'demo' video type.")
            result_url = generate_drillplayer_demo_hf(test_id, drills_data_str, output_filename)
            return {"video_path": result_url}
        else:
            raise ValueError(f"Unknown video_type: {video_type}")
    except Exception as e:
        print(f"Error in generate_video_api: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Gradio Interface for manual testing (optional)
    with gr.Blocks() as demo:
        gr.Markdown("# Tachelhit Video Generator")
        gr.Markdown("This space generates YouTube Shorts and Drill Player demo videos.")

        with gr.Tab("Generate Short"):
            short_drill_id = gr.Number(label="Drill ID")
            short_drill_data = gr.Textbox(label="Drill Data (JSON String)", lines=5)
            short_output_filename = gr.Textbox(label="Output Filename (e.g., short_123.mp4)")
            short_output = gr.Video(label="Generated Short")
            short_button = gr.Button("Generate YouTube Short")
            short_button.click(
                fn=lambda id, data, filename: generate_video_api("short", drill_id=id, drill_data_str=data, output_filename=filename),
                inputs=[short_drill_id, short_drill_data, short_output_filename],
                outputs=short_output
            )

        with gr.Tab("Generate Demo"):
            demo_test_id = gr.Number(label="Test ID")
            demo_drills_data = gr.Textbox(label="Drills Data (JSON String)", lines=10)
            demo_output_filename = gr.Textbox(label="Output Filename (e.g., demo_456.mp4)")
            demo_output = gr.Video(label="Generated Demo Video")
            demo_button = gr.Button("Generate Drill Player Demo")
            demo_button.click(
                fn=lambda id, data, filename: generate_video_api("demo", test_id=id, drills_data_str=data, output_filename=filename),
                inputs=[demo_test_id, demo_drills_data, demo_output_filename],
                outputs=demo_output
            )

    # Launch Gradio app with an API endpoint
    # The `api_name` parameter makes the function available as an API endpoint
    # that can be called by the FastAPI backend.
    demo.launch(share=True, enable_queue=True, server_port=int(os.environ.get("PORT", 7860)))
    
    # You might also want to expose a raw FastAPI route for direct calls
    # app = gr.mount_gradio_app(FastAPI(), demo.app, path="/") # Example for mounting, but launch handles it

