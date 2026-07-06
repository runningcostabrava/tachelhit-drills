#!/usr/bin/env python3
"""
Local YouTube -> Tachelhit drills helper.

Downloads a YouTube video ON THIS COMPUTER (your own residential IP, which
YouTube does NOT block the way it blocks Render's datacenter IP), then hands the
file to the Render backend, which does the rest server-side:
transcribe -> correct -> translate -> create drills. The drills then show up in
the app.

Install once:
    pip install yt-dlp requests
    # and have ffmpeg on your PATH (for audio extraction)

Use:
    python capture_youtube.py "https://www.youtube.com/watch?v=..."
    python capture_youtube.py "<url>" --tag lesson1 --lang shi --audio-only

Config (optional env vars):
    TACHELHIT_API      backend base URL (default: the Render URL below)
    TACHELHIT_API_KEY  X-API-Key, only if the backend enforces one
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
import time

try:
    import requests
except ImportError:
    sys.exit("Missing dependency. Run:  pip install requests yt-dlp")

API_BASE = os.getenv("TACHELHIT_API", "https://tachelhit-drills-api.onrender.com").rstrip("/")
API_KEY = os.getenv("TACHELHIT_API_KEY", "")


def _headers():
    return {"X-API-Key": API_KEY} if API_KEY else {}


def download(url, out_dir, audio_only):
    fmt = "bestaudio/best" if audio_only else "best[height<=720][ext=mp4]/best[height<=720]/best"
    out_tmpl = os.path.join(out_dir, "video.%(ext)s")
    cmd = [sys.executable, "-m", "yt_dlp", "-f", fmt, "-o", out_tmpl, "--no-playlist", url]
    print(f"[download] {url}")
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        sys.exit("yt-dlp not installed. Run:  pip install yt-dlp")
    except subprocess.CalledProcessError as e:
        sys.exit(f"Download failed ({e.returncode}). Is the URL valid / video available?")
    files = glob.glob(os.path.join(out_dir, "video.*"))
    if not files:
        sys.exit("Download produced no file.")
    path = max(files, key=os.path.getsize)
    print(f"[download] saved {os.path.basename(path)} ({os.path.getsize(path) // 1024} KB)")
    return path


def upload(path, tag, lang, audio_only):
    data = {"apply_correction": "true"}
    if tag:
        data["tag"] = tag
    if lang:
        data["language"] = lang
    print(f"[upload] -> {API_BASE}/video-analysis/auto-drills-upload")
    with open(path, "rb") as f:
        r = requests.post(
            f"{API_BASE}/video-analysis/auto-drills-upload",
            files={"video": (os.path.basename(path), f, "application/octet-stream")},
            data=data, headers=_headers(), timeout=900,
        )
    if r.status_code != 200:
        sys.exit(f"Upload failed: HTTP {r.status_code} {r.text[:300]}")
    return r.json()


def poll(job_id):
    print(f"[poll] job {job_id} (Render is transcribing/translating/creating drills)…")
    last = None
    while True:
        r = requests.get(f"{API_BASE}/video-analysis/job/{job_id}", headers=_headers(), timeout=60)
        if r.status_code != 200:
            print(f"  (poll HTTP {r.status_code}, retrying)")
            time.sleep(6)
            continue
        j = r.json()
        st = j.get("status")
        if st != last:
            print(f"  status: {st}")
            last = st
        if st == "FAILED":
            sys.exit(f"Pipeline failed: {j.get('processing_log') or j}")
        if st == "COMPLETED" or j.get("drills_created") is not None:
            return j
        time.sleep(6)


def main():
    ap = argparse.ArgumentParser(description="Download a YouTube video locally and turn it into Tachelhit drills on Render.")
    ap.add_argument("url", help="YouTube (or other yt-dlp-supported) URL")
    ap.add_argument("--tag", help="tag to put on the created drills")
    ap.add_argument("--lang", help="ASR language hint, e.g. shi")
    ap.add_argument("--audio-only", action="store_true", help="download audio only (faster)")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as d:
        path = download(args.url, d, args.audio_only)
        res = upload(path, args.tag, args.lang, args.audio_only)
        job_id = res.get("job_id")
        if not job_id:
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return
        final = poll(job_id)
    made = final.get("drills_created")
    print(f"\n[done] status={final.get('status')} · drills_created={made}")
    print("Open the app's Drills list to review them.")


if __name__ == "__main__":
    main()
