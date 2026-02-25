import os
import subprocess
import json
import requests
import tempfile
import shutil
from moviepy.video.io.VideoFileClip import VideoFileClip

# CONFIGURATION
API_BASE = "https://tachelhit-drills-api.onrender.com"

def run_yt_dlp(url, cookie_file=None):
    """Downloads video and subtitles locally with high resiliency."""
    print(f"🚀 Attempting to download: {url}")
    
    # 1. Clean URL
    clean_url = url.split('&t=')[0] if '&t=' in url else url
    
    # 2. Get Metadata
    print("📡 Fetching metadata...")
    cmd_meta = ["yt-dlp", "--skip-download", "--print-json", "--no-check-certificates", clean_url]
    if cookie_file: cmd_meta.extend(["--cookies", cookie_file])
    
    result = subprocess.run(cmd_meta, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ Metadata fetch failed: {result.stderr[:200]}")
        return None
        
    info = json.loads(result.stdout)
    video_id = info['id']
    title = info['title']
    
    # 3. Download Video
    print(f"📦 Downloading video: {title}")
    video_path = os.path.join(os.getcwd(), f"{video_id}.mp4")
    
    # Try multiple format options
    formats = ["bestvideo[height<=720]+bestaudio/best[height<=720]", "best", "mp4"]
    success = False
    for fmt in formats:
        print(f"   Trying format: {fmt}...")
        cmd_dl = [
            "yt-dlp", "-f", fmt, "--merge-output-format", "mp4",
            "-o", video_path, "--no-check-certificates", clean_url
        ]
        if cookie_file: cmd_dl.extend(["--cookies", cookie_file])
        
        dl_res = subprocess.run(cmd_dl)
        if dl_res.returncode == 0 and os.path.exists(video_path):
            success = True
            break
            
    if not success:
        print("❌ All download attempts failed.")
        return None

    # 4. Download Subtitles
    print(f"📝 Fetching subtitles...")
    cmd_subs = [
        "yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs",
        "--sub-langs", "en.*", "--convert-subs", "vtt", 
        "-o", os.path.join(os.getcwd(), f"{video_id}"), clean_url
    ]
    if cookie_file: cmd_subs.extend(["--cookies", cookie_file])
    subprocess.run(cmd_subs)
    
    vtt_path = None
    for f in os.listdir("."):
        if f.startswith(video_id) and f.endswith(".vtt"):
            vtt_path = f
            break
            
    return video_path, vtt_path, title

def parse_vtt(vtt_path):
    import re
    segments = []
    timestamp_re = re.compile(r'(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})')
    if not vtt_path or not os.path.exists(vtt_path): return []
    
    with open(vtt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        match = timestamp_re.match(lines[i])
        if match:
            start_str, end_str = match.groups()
            def to_s(t):
                parts = t.split(':')
                return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
            start, end = to_s(start_str), to_s(end_str)
            text = ""
            i += 1
            while i < len(lines) and lines[i].strip() and not timestamp_re.match(lines[i]):
                text += lines[i].strip() + " "
                i += 1
            if text: segments.append({"start": start, "end": end, "text": text.strip()})
        else: i += 1
    return segments

def process_locally(video_path, segments, tag="local_import"):
    video = VideoFileClip(video_path)
    for idx, seg in enumerate(segments):
        print(f"🎬 Processing Segment {idx+1}/{len(segments)}: {seg['text'][:50]}...")
        with tempfile.TemporaryDirectory() as tmp_dir:
            clip_name = f"clip_{idx}.mp4"
            clip_path = os.path.join(tmp_dir, clip_name)
            subclip = video.subclipped(seg['start'], seg['end'])
            subclip.write_videofile(clip_path, codec="libx264", audio_codec="aac", logger=None)
            
            # Create Drill
            try:
                drill_resp = requests.post(f"{API_BASE}/drills/", json={
                    "text_catalan": "VIDEO IMPORT", "text_tachelhit": seg['text'], "tag": tag
                })
                drill_id = drill_resp.json()['id']
                # Upload
                with open(clip_path, 'rb') as f:
                    requests.post(f"{API_BASE}/upload-media/{drill_id}/video", files={"file": (clip_name, f, "video/mp4")})
                print(f"✅ Uploaded Drill #{drill_id}")
            except Exception as e:
                print(f"❌ Failed to upload segment {idx}: {e}")
            subclip.close()
    video.close()

if __name__ == "__main__":
    print("--- TAMAZIGHT VIDEO LOCAL IMPORTER (V2) ---")
    choice = input("Do you have the video file already? (y/n): ").lower()
    
    v_path, s_path, title = None, None, "Manual_Import"
    
    if choice == 'y':
        v_path = input("Enter full path to video file (.mp4): ").strip('"')
        s_path = input("Enter full path to subtitle file (.vtt): ").strip('"')
    else:
        url = input("Enter YouTube URL: ")
        cookies = input("Enter path to cookies.txt (optional): ")
        res = run_yt_dlp(url, cookies if cookies else None)
        if res: v_path, s_path, title = res

    if v_path and os.path.exists(v_path):
        print(f"Processing: {v_path}")
        segments = parse_vtt(s_path)
        if not segments:
            print("No segments found in subtitles. You might need to provide a .vtt file.")
        else:
            limit = input(f"Found {len(segments)} segments. How many to import? (Enter for ALL): ")
            if limit: segments = segments[:int(limit)]
            process_locally(v_path, segments, tag=f"vid_{title[:20]}")
            print("\n✨ ALL DONE!")
    else:
        print("❌ Could not proceed without a valid video file.")
