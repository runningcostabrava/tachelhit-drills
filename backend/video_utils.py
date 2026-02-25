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
        subclip = video.subclip(max(0, start - 0.2), min(video.duration, end + 0.2))
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
