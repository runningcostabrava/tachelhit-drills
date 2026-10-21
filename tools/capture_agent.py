#!/usr/bin/env python3
"""
Tachelhit Capture Agent — download on YOUR computer, let the server make drills.

YouTube blocks downloads from Render's datacenter IP. This agent runs on your own
computer: it watches the backend for URLs you paste in the web app's "Captura"
screen, downloads them on your home IP with yt-dlp, uploads the file to the
backend, and the backend transcribes -> corrects -> translates -> creates drills.

Two ways to use it
  1. The installable build (recommended): download TachelhitCaptureAgent.exe
     (Windows) or TachelhitCaptureAgent-macos.zip from the GitHub release
     "capture-agent" and double-click it ONCE. It copies itself to a per-user
     folder, registers itself to start at login, and lives in the system tray.
  2. As a script:  pip install requests yt-dlp pystray pillow
                   python tools/capture_agent.py --console

Command line
  --api URL[,URL]  backend base URL(s), comma-separated to serve several (default
                   https://tachelhit-drills-api.onrender.com)
  --key KEY        X-API-Key, only if the backend enforces one
  --poll SECONDS   queue check interval (default 8)
  --console        no tray icon; log to the terminal (what the .py defaults to)
  --install        copy to the per-user folder + start at login, then exit
  --process-at URL do the heavy work on a backend on this PC and copy the drills to the
                   backend the request came from (step 1 of local capture)
  --uninstall      remove the start-at-login entry
  --once           process whatever is queued now, then exit (for tests)
  --version

Nothing is sent anywhere except your own backend. yt-dlp (and the deno JS
runtime it needs for YouTube) are fetched from their official GitHub releases
into the agent folder and yt-dlp self-updates once a day, so YouTube changes
don't leave the agent stale.
"""
from __future__ import annotations

import argparse
import glob
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
import zipfile
from datetime import datetime, timedelta, timezone

try:
    import requests
except ImportError:  # the frozen build always has it
    sys.exit("Missing dependency. Run:  pip install requests yt-dlp")

__version__ = "2.6.0"
APP_NAME = "TachelhitCapture"
DEFAULT_API = "https://tachelhit-drills-api.onrender.com"
# Fields copied when a drill made by the local backend is created on the remote one
# (same list as backend/tools/sync_drills_to_prod.py; media URLs point at Cloudinary).
DRILL_FIELDS = ["tag", "author", "text_catalan", "text_tachelhit", "text_arabic", "audio_url", "audio_tts_url",
                "audio_tts_shi_url", "video_url", "image_url", "is_correction_dataset", "video_start_time",
                "video_end_time", "text_tachelhit_latin", "text_tachelhit_suggested", "text_catalan_suggested",
                "draft_check", "variety", "region", "speaker", "source_url", "source_title", "source_channel",
                "source_playlist", "license", "verified"]
WEB_APP = "https://tamazight-drills.vercel.app/video-creator"  # old address tachelhit-drills.vercel.app still answers
YTDLP_RELEASE = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/"
DENO_RELEASE = "https://github.com/denoland/deno/releases/latest/download/"
FFMPEG_WIN = "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/ffmpeg-master-latest-win64-gpl.zip"
FFMPEG_MAC = "https://evermeet.cx/ffmpeg/getrelease/zip"
# Caption languages worth sending to the server, best first. Teaching videos
# often carry the Tamazight word AND its gloss in one cue ("agmar / horse").
SUB_LANGS = ["shi", "ber", "zgh", "tzm", "kab", "ar", "ca", "fr", "es", "en"]
AMAZIGH_SUB_LANGS = SUB_LANGS[:5]  # the only codes an AUTOMATIC caption track may have
KEEP_DOWNLOADS_DAYS = 7
FROZEN = bool(getattr(sys, "frozen", False))
IS_WIN = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
ARM = platform.machine().lower() in ("arm64", "aarch64")


# ---------------------------------------------------------------- paths/config
def app_dir() -> str:
    if IS_WIN:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    elif IS_MAC:
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    d = os.path.join(base, APP_NAME)
    os.makedirs(os.path.join(d, "bin"), exist_ok=True)
    return d


CONFIG_PATH = os.path.join(app_dir(), "config.json")
LOG_PATH = os.path.join(app_dir(), "agent.log")
LOCK_PATH = os.path.join(app_dir(), "agent.lock")


def load_config() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ---------------------------------------------------------------- logging
_console = True
_status_cb = None  # tray hook: (state, text)


def log(msg: str) -> None:
    line = time.strftime("%H:%M:%S") + " " + str(msg)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    if _console:
        try:
            print(line, flush=True)
        except Exception:
            try:
                print(line.encode("ascii", "replace").decode("ascii"), flush=True)
            except Exception:
                pass


def set_status(state: str, text: str) -> None:
    if _status_cb:
        try:
            _status_cb(state, text)
        except Exception:
            pass


def notify_user(title: str, text: str) -> None:
    """Message box when there is no console (frozen windowed build)."""
    log(f"{title}: {text}")
    if FROZEN and IS_WIN and not _console:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)
        except Exception:
            pass


def trim_log() -> None:
    try:
        if os.path.getsize(LOG_PATH) > 2_000_000:
            with open(LOG_PATH, encoding="utf-8", errors="replace") as f:
                tail = f.read()[-500_000:]
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                f.write(tail)
    except Exception:
        pass


def _no_window() -> dict:
    if IS_WIN:
        return {"creationflags": 0x08000000}  # CREATE_NO_WINDOW
    return {}


# ---------------------------------------------------------------- yt-dlp + deno
def ytdlp_binary_name() -> str:
    if IS_WIN:
        return "yt-dlp.exe"
    if IS_MAC:
        return "yt-dlp_macos"
    return "yt-dlp"


def ytdlp_path() -> str:
    return os.path.join(app_dir(), "bin", ytdlp_binary_name())


def deno_path() -> str:
    return os.path.join(app_dir(), "bin", "deno.exe" if IS_WIN else "deno")


def ensure_deno() -> str | None:
    """yt-dlp needs a JavaScript runtime for YouTube (its 'EJS' challenge
    solver); deno is the one it supports by default. Best effort: without it
    yt-dlp still works for most videos, with fewer formats."""
    p = deno_path()
    if os.path.exists(p):
        return p
    if IS_WIN:
        asset = "deno-x86_64-pc-windows-msvc.zip"
    elif IS_MAC:
        asset = "deno-aarch64-apple-darwin.zip" if ARM else "deno-x86_64-apple-darwin.zip"
    else:
        asset = "deno-aarch64-unknown-linux-gnu.zip" if ARM else "deno-x86_64-unknown-linux-gnu.zip"
    try:
        set_status("busy", "Baixant deno (runtime JS)…")
        log("downloading deno from its official release…")
        with urllib.request.urlopen(DENO_RELEASE + asset, timeout=120) as r:
            data = r.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            name = next(n for n in z.namelist() if n.startswith("deno"))
            with z.open(name) as src, open(p, "wb") as dst:
                shutil.copyfileobj(src, dst)
        if not IS_WIN:
            os.chmod(p, 0o755)
        log("deno ready")
        return p
    except Exception as e:
        log(f"(deno unavailable: {e}; YouTube may offer fewer formats)")
        return None


def ffmpeg_path() -> str | None:
    """ffmpeg lets yt-dlp merge YouTube's separate video+audio streams. PATH
    first, then the agent folder, then a static build fetched once."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    p = os.path.join(app_dir(), "bin", "ffmpeg.exe" if IS_WIN else "ffmpeg")
    if os.path.exists(p):
        return p
    try:
        set_status("busy", "Baixant ffmpeg…")
        log("downloading a static ffmpeg build (one time)…")
        url = FFMPEG_WIN if IS_WIN else FFMPEG_MAC if IS_MAC else None
        if not url:
            return None
        tmp = p + ".zip"
        urllib.request.urlretrieve(url, tmp)
        with zipfile.ZipFile(tmp) as z:
            name = next(n for n in z.namelist() if n.replace("\\", "/").endswith("/ffmpeg.exe" if IS_WIN else "ffmpeg") or n in ("ffmpeg", "ffmpeg.exe"))
            with z.open(name) as src, open(p, "wb") as dst:
                shutil.copyfileobj(src, dst)
        os.remove(tmp)
        if not IS_WIN:
            os.chmod(p, 0o755)
        log("ffmpeg ready")
        return p
    except Exception as e:
        log(f"(ffmpeg unavailable: {e}; videos will be audio-only or single-stream)")
        return None


def ensure_ytdlp(cfg: dict) -> str | None:
    """Return a runnable yt-dlp binary path, downloading/updating it when needed.
    None means: fall back to the bundled Python library."""
    path = ytdlp_path()
    try:
        if not os.path.exists(path):
            set_status("busy", "Baixant yt-dlp…")
            log("downloading yt-dlp from its official release…")
            urllib.request.urlretrieve(YTDLP_RELEASE + ytdlp_binary_name(), path)
            if not IS_WIN:
                os.chmod(path, 0o755)
            cfg["ytdlp_updated"] = datetime.now(timezone.utc).isoformat()
            save_config(cfg)
            log("yt-dlp ready")
        else:
            last = cfg.get("ytdlp_updated")
            stale = True
            if last:
                try:
                    then = datetime.fromisoformat(last)
                    if then.tzinfo is None:  # written by agent 2.0 (naive UTC)
                        then = then.replace(tzinfo=timezone.utc)
                    stale = datetime.now(timezone.utc) - then > timedelta(days=1)
                except ValueError:
                    pass
            if stale:
                log("checking yt-dlp updates…")
                subprocess.run([path, "-U"], capture_output=True, timeout=300, **_no_window())
                cfg["ytdlp_updated"] = datetime.now(timezone.utc).isoformat()
                save_config(cfg)
        return path
    except Exception as e:
        log(f"(yt-dlp binary unavailable: {e}; using the bundled library)")
        return None


def download(url: str, out_dir: str, audio_only: bool, cfg: dict) -> tuple[str, str | None, str | None, str | None]:
    """Download the media (and the best caption track, if any) into out_dir.
    Returns (media_path, subtitles_path, captions_lang, captions_kind)."""
    binary = ensure_ytdlp(cfg)
    deno = ensure_deno()
    ffmpeg = None if audio_only else ffmpeg_path()
    if audio_only:
        fmt = "bestaudio[ext=m4a]/bestaudio/best"
    elif ffmpeg:
        fmt = "bv*[height<=720][ext=mp4]+ba[ext=m4a]/bv*[height<=720]+ba/b[height<=720]/b"
    else:  # no merger: a combined stream, else fall back to audio so drills still get sound
        fmt = "b[height<=720]/b/bestaudio"
    out_tmpl = os.path.join(out_dir, "video.%(ext)s")
    common = ["--no-playlist", "--no-progress", "--no-update", "-o", out_tmpl]
    if deno:
        common += ["--js-runtimes", f"deno:{deno}"]
    if ffmpeg:
        common += ["--ffmpeg-location", ffmpeg, "--merge-output-format", "mp4"]

    def run(args):
        if binary:
            subprocess.run([binary] + args, check=True, capture_output=True, timeout=1800, **_no_window())
        else:
            import yt_dlp  # bundled fallback
            opts = {"format": fmt, "outtmpl": out_tmpl, "noplaylist": True, "quiet": True}
            if "--write-subs" in args or "--write-auto-subs" in args:
                opts.update({"skip_download": True, "writesubtitles": "--write-subs" in args,
                             "writeautomaticsub": "--write-auto-subs" in args,
                             "subtitleslangs": SUB_LANGS, "subtitlesformat": "vtt"})
            with yt_dlp.YoutubeDL(opts) as y:
                y.download([url])

    run(["-f", fmt] + common + [url])
    files = [f for f in glob.glob(os.path.join(out_dir, "video.*")) if not f.endswith(".vtt")]
    if not files:
        raise RuntimeError("download produced no file")
    media = max(files, key=os.path.getsize)

    # Captions: uploaded ones first (human-made), automatic ones only if none —
    # and automatic ones only in an Amazigh code: YouTube has no Tachelhit speech
    # recognition, so its automatic Arabic/French/English track on a Tachelhit
    # video is noise that must never become drill text.
    subs = sub_lang = sub_kind = None
    for flag in ("--write-subs", "--write-auto-subs"):
        wanted = SUB_LANGS if flag == "--write-subs" else AMAZIGH_SUB_LANGS
        try:
            run(["--skip-download", flag, "--sub-langs", ",".join(f"{l}.*" if flag == "--write-subs" else l for l in wanted),
                 "--sub-format", "vtt"] + common + [url])
        except Exception as e:
            log(f"  (captions {flag}: {e})")
        found = {}
        for f in glob.glob(os.path.join(out_dir, "video.*.vtt")):
            code = os.path.basename(f).split(".")[-2].split("-")[0].lower()  # en-US -> en
            found.setdefault(code, f)
        for lang in wanted:
            if lang in found:
                subs, sub_lang = found[lang], lang
                break
        if subs:
            sub_kind = "uploaded" if flag == "--write-subs" else "automatic"
            log(f"  captions: {os.path.basename(subs)} ({sub_kind})")
            break
    return media, subs, sub_lang, sub_kind


def source_meta(url: str, cfg: dict) -> dict:
    """Title, channel, playlist and licence of the video, for the credit line on
    every drill. Playlist titles are cached per list id (one listing call)."""
    binary = ensure_ytdlp(cfg)
    deno = ensure_deno()
    extra = ["--js-runtimes", f"deno:{deno}"] if deno else []
    meta: dict = {}
    try:
        if binary:
            out = subprocess.run([binary, "--no-playlist", "--skip-download", "--no-warnings",
                                  "--encoding", "utf-8", "--print", "%(title)s\t%(channel)s\t%(license)s", url] + extra,
                                 capture_output=True, timeout=120, text=True, encoding="utf-8", errors="replace",
                                 **_no_window()).stdout.strip().splitlines()
            if out:
                t, c, lic = (out[-1].split("\t") + ["", "", ""])[:3]
                meta = {"title": t, "channel": c, "license": "" if lic in ("NA", "None") else lic}
        else:
            import yt_dlp
            with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True, "skip_download": True}) as y:
                info = y.extract_info(url, download=False) or {}
            meta = {"title": info.get("title") or "", "channel": info.get("channel") or info.get("uploader") or "",
                    "license": info.get("license") or ""}
        m = re.search(r"[?&]list=([A-Za-z0-9_-]+)", url)
        if m:
            lid = m.group(1)
            cache = cfg.setdefault("playlists", {})
            if lid not in cache and binary:
                out = subprocess.run([binary, "--flat-playlist", "--skip-download", "--no-warnings", "--playlist-items", "1",
                                      "--encoding", "utf-8", "--print", "%(playlist_title)s", f"https://www.youtube.com/playlist?list={lid}"] + extra,
                                     capture_output=True, timeout=120, text=True, encoding="utf-8", errors="replace",
                                     **_no_window()).stdout.strip().splitlines()
                cache[lid] = (out[-1] if out else "").strip()
                save_config(cfg)
            if cache.get(lid) and cache[lid] not in ("NA", "None"):
                meta["playlist"] = cache[lid]
    except Exception as e:
        log(f"  (metadata unavailable: {e})")
    return meta


def purge_old_downloads() -> None:
    root = os.path.join(app_dir(), "downloads")
    cutoff = time.time() - KEEP_DOWNLOADS_DAYS * 86400
    try:
        for d in glob.glob(os.path.join(root, "*")):
            if os.path.isdir(d) and os.path.getmtime(d) < cutoff:
                shutil.rmtree(d, ignore_errors=True)
    except Exception:
        pass


# ---------------------------------------------------------------- queue worker
class Agent:
    def __init__(self, api: str, api_key: str, poll: int, cfg: dict):
        # One agent can serve several backends (e.g. production + a local dev
        # server): each request is answered to the backend that queued it.
        self.apis = [a.strip().rstrip("/") for a in api.split(",") if a.strip()]
        self.api = self.apis[0]
        self.poll = poll
        self.cfg = cfg
        # Where the heavy work runs. When set, a request claimed from another backend is
        # uploaded HERE (a backend on this PC: no memory limit, no shared instance), and
        # the drills it makes are copied to the backend the request came from.
        self.process_at = (cfg.get("process_at") or "").rstrip("/") or None
        self.hdrs = {"X-Agent-Version": __version__}
        if api_key:
            self.hdrs["X-API-Key"] = api_key
        self.stop = threading.Event()
        self.done_count = 0

    def handle(self, req: dict, api: str | None = None) -> None:
        api = api or self.api
        rid = req["id"]
        log(f"claimed request #{rid}: {req['url']}")
        set_status("busy", f"Descarregant #{rid}…")
        # Kept for KEEP_DOWNLOADS_DAYS so the owner can inspect what was sent.
        d = os.path.join(app_dir(), "downloads", f"{time.strftime('%Y%m%d-%H%M%S')}_req{rid}")
        os.makedirs(d, exist_ok=True)
        if True:
            try:
                path, subs, sub_lang, sub_kind = download(req["url"], d, req.get("audio_only", True), self.cfg)
                log(f"  downloaded {os.path.basename(path)} ({os.path.getsize(path)//1024} KB) -> {d}; uploading...")
                set_status("busy", f"Pujant #{rid}…")
                data = {"apply_correction": str(bool(req.get("apply_correction", True))).lower(),
                        "source_url": req["url"]}  # provenance on every drill
                meta = source_meta(req["url"], self.cfg)
                for k in ("title", "channel", "playlist", "license"):
                    if meta.get(k):
                        data[f"source_{k}"] = meta[k]
                if meta.get("title"):
                    log(f"  source: {meta.get('channel')} — {meta['title']}" + (f" [{meta['playlist']}]" if meta.get("playlist") else ""))
                if req.get("tag"):
                    data["tag"] = req["tag"]
                if req.get("language"):
                    data["language"] = req["language"]
                if req.get("variety"):
                    data["variety"] = req["variety"]
                files = {"video": (os.path.basename(path), open(path, "rb"), "application/octet-stream")}
                if subs:
                    files["subtitles"] = (os.path.basename(subs), open(subs, "rb"), "text/vtt")
                    data["captions_lang"] = sub_lang or ""
                    data["captions_kind"] = sub_kind or ""
                target = self._processing_backend(api)
                try:
                    r = requests.post(
                        f"{target}/video-analysis/auto-drills-upload",
                        files=files, data=data, headers=self.hdrs, timeout=900,
                    )
                finally:
                    for _, fh, _ in files.values():
                        fh.close()
                r.raise_for_status()
                job_id = r.json().get("job_id")
                if target == api:
                    requests.post(f"{api}/capture/{rid}/done", json={"job_id": job_id}, headers=self.hdrs, timeout=60)
                    self.done_count += 1
                    log(f"  uploaded -> pipeline job {job_id}. The server is making drills.")
                    set_status("idle", f"Fet #{rid} · el servidor crea els drills")
                else:
                    log(f"  uploaded to {target} -> local job {job_id}; processing on this PC...")
                    set_status("busy", f"Processant #{rid} en aquest PC…")
                    job = self._wait_job(target, job_id)
                    if job.get("status") != "COMPLETED":
                        raise RuntimeError(f"local job {job_id} {job.get('status')}: {job.get('error_message') or ''}"[:300])
                    created = job.get("drills_created") or []
                    n_new, n_dup = self._copy_drills(target, api, created)
                    requests.post(f"{api}/capture/{rid}/done", json={"job_id": job_id, "drills_created": n_new},
                                  headers=self.hdrs, timeout=60)
                    self.done_count += 1
                    skipped = len(job.get("media_errors") or [])
                    log(f"  done: {len(created)} drills made here, {n_new} copied to {api}" + (f", {n_dup} already there" if n_dup else "")
                        + (f"; {skipped} lines without a clip" if skipped else ""))
                    set_status("idle", f"Fet #{rid} · {n_new} drills pujats")
            except subprocess.CalledProcessError as e:
                err = (e.stderr or b"").decode("utf-8", "replace").strip().splitlines()
                msg = err[-1] if err else f"yt-dlp exit {e.returncode}"
                self.fail(rid, msg, api)
            except Exception as e:
                self.fail(rid, str(e), api)

    def fail(self, rid: int, msg: str, api: str | None = None) -> None:
        api = api or self.api
        log(f"  FAILED #{rid}: {msg}")
        set_status("error", f"Ha fallat #{rid}: {msg[:80]}")
        try:
            requests.post(f"{api}/capture/{rid}/fail", json={"error": msg[:400]}, headers=self.hdrs, timeout=60)
        except Exception:
            pass

    def _processing_backend(self, api: str) -> str:
        """The local backend when configured and awake; otherwise the backend the request came from."""
        if not self.process_at or self.process_at == api:
            return api
        try:
            r = requests.get(f"{self.process_at}/health", timeout=10)
            if r.status_code == 200:
                return self.process_at
            log(f"  (local backend {self.process_at} answered {r.status_code}; processing on {api})")
        except Exception as e:
            log(f"  (local backend {self.process_at} not reachable: {e}; processing on {api})")
        return api

    def _wait_job(self, api: str, job_id: int, max_minutes: int = 45) -> dict:
        """Poll the pipeline job until it ends. On this PC a job cannot be killed by a deploy."""
        t0 = time.time()
        last = ""
        while time.time() - t0 < max_minutes * 60 and not self.stop.is_set():
            try:
                job = requests.get(f"{api}/video-analysis/job/{job_id}", headers=self.hdrs, timeout=60).json()
            except Exception as e:
                log(f"  (job poll error: {e})"); time.sleep(15); continue
            st = job.get("status") or ""
            if st != last:
                log(f"  job {job_id}: {st}"); last = st
            if st in ("COMPLETED", "FAILED"):
                return job
            time.sleep(10)
        return {"status": "TIMEOUT", "error_message": f"no result after {max_minutes} min"}

    def _copy_drills(self, src_api: str, dst_api: str, ids: list) -> tuple:
        """Create on dst the drills src made (rows only; media is on Cloudinary). A drill that
        dst already has (same source + second + Tachelhit text) is skipped."""
        if not ids:
            return 0, 0
        rows = requests.get(f"{src_api}/drills/", params={"ids": ",".join(str(i) for i in ids)}, headers=self.hdrs, timeout=120).json()
        rows = [d for d in rows if d.get("id") in set(ids)]
        existing = {}
        try:
            for d in requests.get(f"{dst_api}/drills/", headers=self.hdrs, timeout=180).json():
                existing[self._drill_key(d)] = d["id"]
        except Exception as e:
            log(f"  (could not list {dst_api} drills for duplicate check: {e})")
        n_new = n_dup = 0
        for d in sorted(rows, key=lambda x: (float(x.get("video_start_time") or 0), x["id"])):
            if self._drill_key(d) in existing:
                n_dup += 1
                continue
            body = {k: d.get(k) for k in DRILL_FIELDS if d.get(k) is not None}
            r = requests.post(f"{dst_api}/drills/", json=body, headers=self.hdrs, timeout=120)
            r.raise_for_status()
            n_new += 1
        return n_new, n_dup

    @staticmethod
    def _drill_key(d: dict) -> tuple:
        if d.get("source_url"):
            return ("src", d["source_url"], round(float(d.get("video_start_time") or 0), 1), (d.get("text_tachelhit") or "").strip())
        return ("txt", d.get("tag") or "", (d.get("text_catalan") or "").strip(), (d.get("text_tachelhit") or "").strip())

    def run(self, once: bool = False) -> None:
        purge_old_downloads()
        log(f"agent v{__version__} started - backends {', '.join(self.apis)} - polling every {self.poll}s")
        set_status("idle", "Connectat · esperant URLs")
        errors = {a: 0 for a in self.apis}
        while not self.stop.is_set():
            handled = False
            for api in self.apis:
                try:
                    r = requests.get(f"{api}/capture/pending", headers=self.hdrs, timeout=40)
                    req = (r.json() or {}).get("request") if r.status_code == 200 else None
                    errors[api] = 0
                    if req:
                        self.handle(req, api)
                        handled = True
                except Exception as e:
                    errors[api] += 1
                    if errors[api] <= 3 or errors[api] % 50 == 0:
                        log(f"(poll error {api}: {e})")
            if all(v > 2 for v in errors.values()):
                set_status("error", "Sense connexió amb cap servidor")
            elif not handled:
                set_status("idle", "Connectat · esperant URLs")
            if handled:
                continue  # check again right away in case more are queued
            if once:
                return
            self.stop.wait(min(self.poll * (2 if min(errors.values()) > 5 else 1), 60))


# ---------------------------------------------------------------- install
def install_dir() -> str:
    return app_dir()


def installed_exe() -> str:
    return os.path.join(install_dir(), "TachelhitCaptureAgent.exe" if IS_WIN else "TachelhitCaptureAgent")


def startup_entry() -> str:
    if IS_WIN:
        return os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu",
                            "Programs", "Startup", "Tachelhit Capture Agent.lnk")
    if IS_MAC:
        return os.path.expanduser("~/Library/LaunchAgents/com.tachelhit.capture.plist")
    return os.path.expanduser("~/.config/autostart/tachelhit-capture.desktop")


def do_install(args) -> str:
    """Copy the frozen executable to the per-user folder and register autostart."""
    if not FROZEN:
        raise SystemExit("--install is for the packaged build; as a script see tools/README.md.")
    target = installed_exe()
    src = os.path.abspath(sys.executable)
    if os.path.abspath(src) != os.path.abspath(target):
        shutil.copy2(src, target)
        if not IS_WIN:
            os.chmod(target, 0o755)
    cfg = load_config()
    if args.api:
        cfg["api"] = args.api
    if args.key:
        cfg["api_key"] = args.key
    cfg.setdefault("api", DEFAULT_API)
    save_config(cfg)
    entry = startup_entry()
    os.makedirs(os.path.dirname(entry), exist_ok=True)
    if IS_WIN:
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{entry}');"
              f"$s.TargetPath='{target}';$s.WorkingDirectory='{install_dir()}';"
              f"$s.Description='Tachelhit Capture Agent';$s.Save()")
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                       check=True, capture_output=True, **_no_window())
    elif IS_MAC:
        with open(entry, "w") as f:
            f.write(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                '<plist version="1.0"><dict>\n'
                '  <key>Label</key><string>com.tachelhit.capture</string>\n'
                f'  <key>ProgramArguments</key><array><string>{target}</string></array>\n'
                '  <key>RunAtLoad</key><true/>\n'
                '  <key>KeepAlive</key><false/>\n'
                '</dict></plist>\n')
    else:
        with open(entry, "w") as f:
            f.write("[Desktop Entry]\nType=Application\nName=Tachelhit Capture Agent\n"
                    f"Exec={target}\nX-GNOME-Autostart-enabled=true\n")
    log(f"installed to {target}; autostart entry {entry}")
    return target


def do_uninstall() -> None:
    for p in (startup_entry(), LOCK_PATH):
        try:
            os.remove(p)
        except FileNotFoundError:
            pass
    notify_user("Agent de captura", "Desinstal·lat: ja no s'engegarà en iniciar sessió.\n"
                f"Pots esborrar la carpeta {install_dir()} si vols.")


def acquire_lock() -> bool:
    """One agent per user: refuse to start if another instance is alive."""
    try:
        if os.path.exists(LOCK_PATH):
            with open(LOCK_PATH) as f:
                pid = int(f.read().strip() or 0)
            if pid and pid != os.getpid() and _pid_alive(pid):
                return False
        with open(LOCK_PATH, "w") as f:
            f.write(str(os.getpid()))
        return True
    except Exception:
        return True


def _pid_alive(pid: int) -> bool:
    if IS_WIN:
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        ctypes.windll.kernel32.CloseHandle(h)
        return True
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------- tray
def run_tray(agent: Agent) -> None:
    """System-tray icon with live status; falls back to console mode if pystray is missing."""
    global _status_cb
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        log("(pystray/Pillow not available: running in console mode)")
        agent.run()
        return

    colors = {"idle": (46, 75, 140), "busy": (217, 119, 6), "error": (190, 24, 93)}

    def make_icon(state: str) -> Image.Image:
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((2, 2, 62, 62), radius=14, fill=colors.get(state, colors["idle"]))
        # a stylised yaz: vertical bar + two arcs
        d.line((32, 14, 32, 50), fill="white", width=6)
        d.arc((14, 4, 50, 34), 0, 180, fill="white", width=6)
        d.arc((14, 30, 50, 60), 180, 360, fill="white", width=6)
        return img

    status = {"state": "idle", "text": "Engegant…"}

    def on_status(state: str, text: str) -> None:
        status.update(state=state, text=text)
        try:
            icon.icon = make_icon(state)
            icon.title = f"Tachelhit Capture · {text}"
            icon.update_menu()
        except Exception:
            pass

    def quit_(icon_, _item):
        agent.stop.set()
        icon_.stop()

    menu = pystray.Menu(
        pystray.MenuItem(lambda _i: status["text"], None, enabled=False),
        pystray.MenuItem(lambda _i: f"Captures fetes: {agent.done_count}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Obre l'app (Captura)", lambda: webbrowser.open(WEB_APP)),
        pystray.MenuItem("Obre el registre", lambda: _open_path(LOG_PATH)),
        pystray.MenuItem("Obre la carpeta de l'agent", lambda: _open_path(install_dir())),
        pystray.MenuItem("Obre les descàrregues", lambda: _open_path(os.path.join(install_dir(), "downloads"))),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"Versió {__version__}", None, enabled=False),
        pystray.MenuItem("Surt", quit_),
    )
    icon = pystray.Icon("tachelhit-capture", make_icon("idle"), "Tachelhit Capture", menu)
    _status_cb = on_status
    threading.Thread(target=agent.run, daemon=True).start()
    icon.run()


def _open_path(p: str) -> None:
    try:
        if IS_WIN:
            os.startfile(p)  # type: ignore[attr-defined]
        elif IS_MAC:
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])
    except Exception as e:
        log(f"(cannot open {p}: {e})")


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    global _console
    ap = argparse.ArgumentParser(description="Tachelhit capture agent")
    ap.add_argument("--api", help=f"backend URL (default {DEFAULT_API})")
    ap.add_argument("--key", help="X-API-Key if the backend enforces one")
    ap.add_argument("--poll", type=int, help="seconds between queue checks (default 8)")
    ap.add_argument("--process-at", dest="process_at",
                    help="backend on this PC that does the heavy work (e.g. http://127.0.0.1:8000); "
                         "drills it makes are copied to the backend the request came from. '' to disable")
    ap.add_argument("--console", action="store_true", help="no tray icon, log to the terminal")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--once", action="store_true", help="process the queue once and exit")
    ap.add_argument("--version", action="version", version=f"TachelhitCaptureAgent {__version__}")
    args = ap.parse_args(argv)

    trim_log()
    cfg = load_config()
    # env vars keep working for scripted use; CLI flags win; config.json remembers.
    api = args.api or os.getenv("TACHELHIT_API") or cfg.get("api") or DEFAULT_API
    key = args.key or os.getenv("TACHELHIT_API_KEY") or cfg.get("api_key", "")
    poll = args.poll or int(os.getenv("CAPTURE_POLL_SECS") or cfg.get("poll") or 8)
    if args.api or args.key or args.poll or args.process_at is not None:
        cfg.update({k: v for k, v in (("api", args.api), ("api_key", args.key), ("poll", args.poll)) if v})
        if args.process_at is not None:
            cfg["process_at"] = args.process_at.strip()
        save_config(cfg)

    if args.uninstall:
        do_uninstall()
        return 0
    if args.install:
        target = do_install(args)
        notify_user("Agent de captura", f"Instal·lat. S'engegarà sol en iniciar sessió.\n{target}")
        return 0

    # Frozen build, double-clicked from the Downloads folder: install itself and
    # hand over to the installed copy, so one click is the whole setup.
    if FROZEN and not args.once and os.path.abspath(sys.executable) != os.path.abspath(installed_exe()):
        _console = False
        try:
            target = do_install(args)
        except Exception as e:
            notify_user("Agent de captura", f"No s'ha pogut instal·lar: {e}")
            return 1
        subprocess.Popen([target], cwd=install_dir(), close_fds=True, **_no_window())
        notify_user("Agent de captura", "Instal·lat i en marxa a la safata del sistema.\n"
                    "S'engegarà sol cada cop que iniciïs sessió.\n"
                    "Ja pots enganxar URLs a la pantalla Captura de l'app.")
        return 0

    _console = args.console or not FROZEN
    if not acquire_lock():
        notify_user("Agent de captura", "Ja hi ha un agent en marxa (mira la safata del sistema).")
        return 0

    agent = Agent(api, key, poll, cfg)
    try:
        if args.once or _console:
            agent.run(once=args.once)
        else:
            run_tray(agent)
    except KeyboardInterrupt:
        log("agent stopped.")
    finally:
        try:
            os.remove(LOCK_PATH)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
