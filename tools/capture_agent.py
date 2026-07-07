#!/usr/bin/env python3
"""
Tachelhit local capture AGENT — run once, then forget it.

Runs quietly in the background on your computer. It polls the Render backend for
queued capture requests; when you paste a URL in the web app, this agent grabs
it, downloads the video on YOUR residential IP (which YouTube doesn't block),
and uploads it back to Render, which transcribes → translates → makes drills.
You never run anything per-video — you just use the web app.

Install once:
    pip install yt-dlp requests
    # and have ffmpeg on your PATH

Run it (leave it running; or set it to auto-start at login — see tools/README):
    python capture_agent.py

Config (optional env vars):
    TACHELHIT_API      backend base URL (default: the Render URL below)
    TACHELHIT_API_KEY  X-API-Key, only if the backend enforces one
    CAPTURE_POLL_SECS  how often to check the queue (default 8)
"""
import glob
import os
import subprocess
import sys
import tempfile
import time

try:
    import requests
except ImportError:
    sys.exit("Missing dependency. Run:  pip install requests yt-dlp")

API = os.getenv("TACHELHIT_API", "https://tachelhit-drills-api.onrender.com").rstrip("/")
API_KEY = os.getenv("TACHELHIT_API_KEY", "")
POLL = int(os.getenv("CAPTURE_POLL_SECS", "8"))
HDRS = {"X-API-Key": API_KEY} if API_KEY else {}


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def download(url, out_dir, audio_only):
    fmt = "bestaudio/best" if audio_only else "best[height<=720][ext=mp4]/best[height<=720]/best"
    out_tmpl = os.path.join(out_dir, "video.%(ext)s")
    subprocess.run(
        [sys.executable, "-m", "yt_dlp", "-f", fmt, "-o", out_tmpl, "--no-playlist", url],
        check=True,
    )
    files = glob.glob(os.path.join(out_dir, "video.*"))
    if not files:
        raise RuntimeError("download produced no file")
    return max(files, key=os.path.getsize)


def handle(req):
    rid = req["id"]
    log(f"claimed request #{rid}: {req['url']}")
    with tempfile.TemporaryDirectory() as d:
        try:
            path = download(req["url"], d, req.get("audio_only", True))
            log(f"  downloaded {os.path.basename(path)} ({os.path.getsize(path)//1024} KB); uploading…")
            data = {"apply_correction": str(bool(req.get("apply_correction", True))).lower()}
            if req.get("tag"):
                data["tag"] = req["tag"]
            if req.get("language"):
                data["language"] = req["language"]
            with open(path, "rb") as f:
                r = requests.post(
                    f"{API}/video-analysis/auto-drills-upload",
                    files={"video": (os.path.basename(path), f, "application/octet-stream")},
                    data=data, headers=HDRS, timeout=900,
                )
            r.raise_for_status()
            job_id = r.json().get("job_id")
            requests.post(f"{API}/capture/{rid}/done", json={"job_id": job_id}, headers=HDRS, timeout=60)
            log(f"  uploaded → pipeline job {job_id}. Render is making drills.")
        except Exception as e:
            log(f"  FAILED: {e}")
            try:
                requests.post(f"{API}/capture/{rid}/fail", json={"error": str(e)[:400]}, headers=HDRS, timeout=60)
            except Exception:
                pass


def main():
    log(f"agent started · backend {API} · polling every {POLL}s. Leave this running.")
    while True:
        try:
            r = requests.get(f"{API}/capture/pending", headers=HDRS, timeout=40)
            req = (r.json() or {}).get("request") if r.status_code == 200 else None
            if req:
                handle(req)
                continue  # check again immediately in case more are queued
        except Exception as e:
            log(f"(poll error: {e})")
        time.sleep(POLL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("agent stopped.")
