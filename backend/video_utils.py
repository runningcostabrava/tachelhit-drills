import os
import yt_dlp
import tempfile
import re
from typing import List, Dict, Any, Optional, Tuple, Generator
from contextlib import contextmanager
from moviepy.video.io.VideoFileClip import VideoFileClip
import cloudinary.uploader
import json
from gradio_client import Client
from deep_translator import GoogleTranslator
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

@contextmanager
def get_yt_dlp_cookie_file(cookies_str: Optional[str] = None) -> Generator[Optional[str], None, None]:
    """
    Context manager to handle yt-dlp cookie file from string or environment.
    """
    if not cookies_str:
        cookies_str = os.getenv("YOUTUBE_COOKIES")
    
    tmp_cookie_file = None
    if cookies_str:
        # If it looks like a path, use it directly
        if os.path.exists(str(cookies_str)) and len(str(cookies_str)) < 255:
            yield cookies_str
            return
        else:
            try:
                # Ensure the cookies start with the Netscape header if they don't already
                header = "# Netscape HTTP Cookie File"
                content = str(cookies_str).strip()
                if not content.startswith(header):
                    content = header + "\n" + content
                
                with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt', encoding='utf-8') as f:
                    f.write(content)
                    tmp_cookie_file = f.name
                yield tmp_cookie_file
            finally:
                if tmp_cookie_file and os.path.exists(tmp_cookie_file):
                    try:
                        os.unlink(tmp_cookie_file)
                    except:
                        pass
    else:
        yield None

def get_video_metadata(url: str, cookies_str: str = None) -> Dict[str, Any]:
    """
    Get video metadata and available subtitles/captions using yt-dlp.
    """
    # Clean URL (remove timestamps which can confuse some extractors during metadata-only phase)
    if '&t=' in url:
        url = url.split('&t=')[0]
    elif '?t=' in url:
        url = url.split('?t=')[0]

    ydl_opts = {
        'skip_download': True,
        'writeautomaticsub': True,
        'writesubtitles': True,
        'quiet': False, 
        'no_warnings': False,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
        'youtube_include_dash_manifest': False,
        'youtube_include_hls_manifest': False,
        'check_formats': False,
        'ignore_no_formats_error': True, # Don't crash if formats are missing
    }
    
    print(f"[VIDEO_UTILS] Analyzing cleaned URL: {url}")

    with get_yt_dlp_cookie_file(cookies_str) as cookie_file:
        if cookie_file:
            ydl_opts['cookiefile'] = cookie_file

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                    return info
                except Exception as e:
                    error_msg = str(e)
                    print(f"[VIDEO_UTILS] yt-dlp error: {error_msg}")
                    
                    if "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
                        raise Exception("YouTube detected a BOT. Your cookies might be EXPIRED. Please refresh your browser, export FRESH cookies, and try again.")
                    
                    if "not available" in error_msg.lower():
                        raise Exception("YouTube says: 'This video is not available'. It is likely GEO-BLOCKED or PRIVATE. Try a different video or upload the file directly.")

                    # Final desperate fallback: Extract metadata ONLY (no formats/subtitles)
                    print("[VIDEO_UTILS] Attempting metadata-only extraction fallback...")
                    ydl_opts['extract_flat'] = True
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl_flat:
                        return ydl_flat.extract_info(url, download=False)
        except Exception as e:
            print(f"[VIDEO_UTILS] Final error: {str(e)}")
            if "YouTube is blocking the server" in str(e) or "YouTube analysis failed" in str(e):
                raise
            raise Exception(f"Error in video metadata extraction: {e}")

def download_video_from_url(url: str, drill_id: int) -> str:
    """
    Download video from URL using yt-dlp and upload to Cloudinary.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        filename = f"import_{drill_id}_{int(datetime.utcnow().timestamp())}.mp4"
        filepath = os.path.join(tmp_dir, filename)
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': filepath,
            'quiet': False,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'referer': 'https://www.google.com/',
        }
        
        with get_yt_dlp_cookie_file() as cookie_file:
            if cookie_file:
                ydl_opts['cookiefile'] = cookie_file
                
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
        if os.path.exists(filepath):
            print(f"[VIDEO_UTILS] Uploading downloaded video to Cloudinary: {filepath}")
            result = cloudinary.uploader.upload(
                filepath, 
                folder="tachelhit/video_imports", 
                resource_type="video"
            )
            return result['secure_url']
        else:
            raise Exception("Failed to download video file")

def download_video_to_dir(url: str, dest_dir: str, cookies_str: Optional[str] = None, audio_only: bool = False) -> Tuple[str, Dict[str, Any]]:
    """
    Download media from any yt-dlp-supported site (YouTube, Instagram, TikTok,
    podcasts, ...) into dest_dir. Returns (local_file_path, info_dict).
    Video is capped at 720p to keep files small enough for ASR and clipping on
    Render; audio_only grabs the best audio track (podcasts, voice content).
    """
    outtmpl = os.path.join(dest_dir, "source.%(ext)s")
    ydl_opts = {
        'format': 'ba[ext=m4a]/ba/b' if audio_only
                  else 'bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/b',
        'outtmpl': outtmpl,
        'noplaylist': True,
        'quiet': False,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
    }
    if not audio_only:
        ydl_opts['merge_output_format'] = 'mp4'

    with get_yt_dlp_cookie_file(cookies_str) as cookie_file:
        if cookie_file:
            ydl_opts['cookiefile'] = cookie_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

    for name in os.listdir(dest_dir):
        if name.startswith("source."):
            path = os.path.join(dest_dir, name)
            print(f"[VIDEO_UTILS] Downloaded {url} -> {path} ({os.path.getsize(path)} bytes)")
            return path, info or {}

    raise Exception("Download finished but no output file was produced")

def parse_vtt(vtt_content: str) -> List[Dict[str, Any]]:
    """
    Minimalistic VTT parser to extract start, end, and text.
    """
    segments = []
    # Regular expression for VTT timestamp lines: 00:00:00.000 --> 00:00:00.000
    timestamp_re = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})')
    
    lines = vtt_content.splitlines()
    i = 0
    while i < len(lines):
        match = timestamp_re.match(lines[i])
        if match:
            start_str, end_str = match.groups()
            
            def to_seconds(t_str):
                parts = t_str.split(':')
                if len(parts) == 3:
                    h, m, s = parts
                else:
                    h = 0
                    m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            
            start = to_seconds(start_str)
            end = to_seconds(end_str)
            
            # Text follows the timestamp line
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() and not timestamp_re.match(lines[i]):
                # Remove HTML tags often found in VTT
                clean_text = re.sub(r'<[^>]+>', '', lines[i].strip())
                if clean_text:
                    text_lines.append(clean_text)
                i += 1
            
            if text_lines:
                segments.append({
                    "start": start,
                    "end": end,
                    "text": " ".join(text_lines)
                })
        else:
            i += 1
            
    return segments

def get_video_segments(url: str, lang: str = 'en', cookies_str: str = None) -> List[Dict[str, Any]]:
    """
    Download subtitles for a specific language and parse them into segments.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        ydl_opts = {
            'skip_download': True,
            'writeautomaticsub': True,
            'writesubtitles': True,
            'subtitleslangs': [lang],
            'outtmpl': os.path.join(tmp_dir, '%(id)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'referer': 'https://www.google.com/',
            'youtube_include_dash_manifest': False,
            'youtube_include_hls_manifest': False,
            'check_formats': False,
            'format': 'best',
        }
        
        with get_yt_dlp_cookie_file(cookies_str) as cookie_file:
            if cookie_file:
                ydl_opts['cookiefile'] = cookie_file
        
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    try:
                        info = ydl.extract_info(url, download=True)
                        video_id = info['id']
                        
                        # Look for subtitle files in tmp_dir
                        for file in os.listdir(tmp_dir):
                            if file.startswith(video_id) and (file.endswith('.vtt') or file.endswith('.srt')):
                                with open(os.path.join(tmp_dir, file), 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    if file.endswith('.vtt'):
                                        return parse_vtt(content)
                        return []
                    except Exception as e:
                        print(f"[VIDEO_UTILS] Error getting segments: {e}")
                        return []
            except Exception as e:
                print(f"[VIDEO_UTILS] Error in getting segments: {e}")
                return []

AUDIO_EXTENSIONS = {'.mp3', '.m4a', '.wav', '.ogg', '.opus', '.aac', '.flac'}

def _has_video_stream(path: str) -> bool:
    """True if the media file actually contains a (non-cover-art) video stream.
    Uses the ffmpeg exe MoviePy ships (ffprobe isn't bundled)."""
    try:
        import subprocess
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            exe = "ffmpeg"
        r = subprocess.run([exe, "-hide_banner", "-i", path], capture_output=True, timeout=30)
        err = r.stderr.decode("utf-8", "ignore")
        # A real video stream shows "Video: <codec>"; cover-art shows mjpeg/png.
        for line in err.splitlines():
            if "Video:" in line and not any(a in line.lower() for a in ("mjpeg", "png", "bmp")):
                return True
        return False
    except Exception:
        return False


def is_audio_file(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    if ext in AUDIO_EXTENSIONS:
        return True
    # Ambiguous containers (.webm/.mkv/.mov/.mp4) can be audio-only — e.g. yt-dlp
    # bestaudio produces webm/opus. Probe for a real video stream; if there's
    # none, treat it as audio so it goes to the (ffmpeg) audio clipper.
    if ext in (".webm", ".mkv", ".mov", ".mp4", ".ogg", ".m4v"):
        return not _has_video_stream(path)
    return False

def process_and_upload_audio_segment(
    audio_path: str,
    start: float,
    end: float,
    drill_id: int
) -> Dict[str, str]:
    """
    Clip an audio segment and upload it to Cloudinary. The audio counterpart of
    process_and_upload_segment for podcast / voice-note sources.

    Uses ffmpeg directly (via the exe MoviePy ships) rather than MoviePy's
    AudioFileClip: MoviePy fails to read webm/opus audio (as produced by yt-dlp
    bestaudio) with "failed to read the first frame", whereas ffmpeg handles it
    — so every audio-only capture would otherwise land drills with no audio.
    """
    import subprocess
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg_exe = "ffmpeg"

    ss = max(0.0, float(start) - 0.1)
    dur = max(0.2, (float(end) + 0.1) - ss)

    with tempfile.TemporaryDirectory() as tmp_dir:
        clip_path = os.path.join(tmp_dir, f"audio_clip_{drill_id}.m4a")
        proc = subprocess.run(
            [ffmpeg_exe, "-y", "-ss", f"{ss:.3f}", "-i", audio_path, "-t", f"{dur:.3f}",
             "-vn", "-acodec", "aac", "-b:a", "128k", clip_path],
            capture_output=True,
        )
        if proc.returncode != 0 or not os.path.exists(clip_path):
            raise OSError(f"ffmpeg audio clip failed: {proc.stderr.decode('utf-8', 'ignore')[-300:]}")

        result = cloudinary.uploader.upload(
            clip_path,
            folder="tachelhit/audio_segments",
            resource_type="video"  # Cloudinary stores audio under the video resource type
        )
        return {"audio_url": result['secure_url']}

def remote_process_and_upload_segment(
    source_url: str, 
    start: float, 
    end: float, 
    drill_id: int
) -> Dict[str, str]:
    """
    Calls the dedicated Video Generator HF Space to clip and thumb,
    then returns the Cloudinary-vaulted URLs.
    """
    space_url = os.getenv("HUGGINGFACE_SPACE_URL")
    if not space_url:
        raise ValueError("HUGGINGFACE_SPACE_URL not configured")
    
    print(f"[REMOTE_CLIP] Requesting clip from HF Space: {start}s - {end}s")
    client = Client(space_url)
    
    clip_data = {
        "source_url": source_url,
        "start_time": start,
        "end_time": end
    }
    
    filename = f"segment_{drill_id}_{int(datetime.utcnow().timestamp())}.mp4"
    
    # Matches api_generate: [type, drill_data, drills_data, filename, test_id]
    result_raw = client.predict(
        "clip",
        json.dumps(clip_data),
        None,
        filename,
        0,
        api_name="/predict"
    )
    
    # Gradio result is usually the direct return value of the function
    print(f"[REMOTE_CLIP] HF Space result: {result_raw}")
    
    # If it's a string, it's likely the JSON response from api_generate
    if isinstance(result_raw, str):
        result = json.loads(result_raw)
    else:
        result = result_raw
    
    # Gradio Client automatically downloads the files returned as 'filepath'
    # We need to upload the file to Cloudinary from the Space's returned temp file.
    
    video_res = cloudinary.uploader.upload(
        result["video_path"], 
        folder="tachelhit/video_segments", 
        resource_type="video"
    )
    thumb_res = cloudinary.uploader.upload(
        result["thumb_path"], 
        folder="tachelhit/image_segments", 
        resource_type="image"
    )
    
    return {
        "video_url": video_res['secure_url'],
        "image_url": thumb_res['secure_url']
    }

def process_and_upload_segment(
    video_path: str, 
    start: float, 
    end: float, 
    drill_id: int
) -> Dict[str, str]:
    """
    Clip video segment, take screenshot, and upload both to Cloudinary.
    """
    # ... rest of function logic remains same as before
    # Re-writing to be complete
    with tempfile.TemporaryDirectory() as tmp_dir:
        clip_path = os.path.join(tmp_dir, f"clip_{drill_id}.mp4")
        thumb_path = os.path.join(tmp_dir, f"thumb_{drill_id}.jpg")
        
        video = VideoFileClip(video_path)
        subclip = video.subclipped(max(0, start - 0.2), min(video.duration, end + 0.2))
        subclip.write_videofile(clip_path, codec="libx264", audio_codec="aac", logger=None)
        
        midpoint = (start + end) / 2 - start
        subclip.save_frame(thumb_path, t=midpoint)
        
        video_result = cloudinary.uploader.upload(clip_path, folder="tachelhit/video_segments", resource_type="video")
        image_result = cloudinary.uploader.upload(thumb_path, folder="tachelhit/image_segments", resource_type="image")
        
        video.close()
        subclip.close()
        
        return {
            "video_url": video_result['secure_url'],
            "image_url": image_result['secure_url']
        }
