"""
OCR Phase-0 Spike — burned-in subtitle reader feasibility test.

Purpose
-------
Answer one question before we build the real OCR feature:
"Can we reliably read the burned-in subtitles off our actual videos, in
Latin, Arabic, and Tifinagh?"

What it does
------------
1. Takes a local video file OR a URL (downloaded with yt-dlp).
2. Samples frames every N seconds.
3. Crops the bottom subtitle band of each frame (where burned-in captions live).
4. Runs each crop through up to three engines:
     - EasyOCR (Latin)   -> Tachelhit romanization
     - EasyOCR (Arabic)
     - Tifinagh HF Space (ayymen/Tifinagh-OCR by default) via gradio_client
5. Writes an HTML report (crop image + each engine's text) you can eyeball to
   decide: reuse the Tifinagh space as-is, fine-tune our own, or defer Tifinagh.

This is a THROWAWAY diagnostic tool, not production code. It deliberately has no
ties to the backend or database.

Setup
-----
    pip install -r local_tools/requirements-ocr-spike.txt
    # (easyocr pulls torch; first run downloads OCR models — be patient)

Usage
-----
    python local_tools/ocr_spike.py --video path/to/clip.mp4
    python local_tools/ocr_spike.py --url "https://youtu.be/XXXX" --interval 4
    python local_tools/ocr_spike.py --video clip.mp4 --band 0.30 --no-tifinagh

Then open the generated report:  ocr_spike_report/report.html

Note on the Tifinagh Space API
------------------------------
The exact gradio endpoint name/signature of a Space can change. If the Tifinagh
calls fail, open the Space page -> "Use via API" and pass the right values with
--tifinagh-space and --tifinagh-api. The script degrades gracefully: any engine
that is unavailable is simply skipped and noted in the report.
"""

import argparse
import base64
import html
import os
import subprocess
import sys
import tempfile

# ---- Optional heavy deps: import lazily / guard so the script still runs
# with whatever subset is installed. -----------------------------------------
try:
    import numpy as np
except ImportError:
    print("FATAL: numpy is required. pip install numpy")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("FATAL: Pillow is required. pip install Pillow")
    sys.exit(1)

try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
except ImportError:
    print("FATAL: moviepy is required. pip install moviepy")
    sys.exit(1)


OUT_DIR = "ocr_spike_report"


def download_url(url: str, work_dir: str) -> str:
    """Download a video to work_dir using yt-dlp; return the local path."""
    print(f"[spike] Downloading {url} ...")
    out_path = os.path.join(work_dir, "input.mp4")
    cmd = [
        "yt-dlp", "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "--merge-output-format", "mp4", "-o", out_path,
        "--no-check-certificates", url,
    ]
    res = subprocess.run(cmd)
    if res.returncode != 0 or not os.path.exists(out_path):
        # Fallback to a simpler format selector
        subprocess.run(["yt-dlp", "-o", out_path, "--no-check-certificates", url])
    if not os.path.exists(out_path):
        raise RuntimeError("yt-dlp failed to download the video.")
    return out_path


def sample_crops(video_path: str, interval: float, band: float, crop_dir: str):
    """
    Sample one frame every `interval` seconds and crop the bottom `band`
    fraction (the subtitle strip). Returns a list of dicts:
        {"t": seconds, "path": crop_png_path}
    Consecutive crops whose pixels are nearly identical are de-duplicated, since
    a burned-in subtitle persists across many frames.
    """
    crops = []
    prev_signature = None
    with VideoFileClip(video_path) as clip:
        duration = clip.duration or 0.0
        h = clip.h
        y0 = int(h * (1.0 - band))
        t = 0.0
        idx = 0
        while t < duration:
            frame = clip.get_frame(t)  # (H, W, 3) uint8
            strip = frame[y0:, :, :]

            # Cheap dedup: downsample-mean signature of the strip.
            sig = strip[::8, ::8, :].mean(axis=(0, 1)).round(1).tobytes()
            if sig != prev_signature:
                prev_signature = sig
                crop_path = os.path.join(crop_dir, f"crop_{idx:04d}_{t:.1f}s.png")
                Image.fromarray(strip).save(crop_path)
                crops.append({"t": round(t, 1), "path": crop_path})
                idx += 1
            t += interval
    print(f"[spike] Sampled {len(crops)} unique subtitle crops "
          f"(interval={interval}s, band=bottom {int(band*100)}%).")
    return crops


def build_easyocr_readers(enable_latin: bool, enable_arabic: bool):
    """Return (latin_reader, arabic_reader); either may be None if disabled/unavailable."""
    latin_reader = arabic_reader = None
    if not (enable_latin or enable_arabic):
        return None, None
    try:
        import easyocr
    except ImportError:
        print("[spike] easyocr not installed -> skipping Latin/Arabic. "
              "pip install easyocr")
        return None, None
    if enable_latin:
        print("[spike] Loading EasyOCR Latin reader (first run downloads models)...")
        latin_reader = easyocr.Reader(["en"], gpu=False)  # 'en' model reads Latin glyphs
    if enable_arabic:
        print("[spike] Loading EasyOCR Arabic reader...")
        arabic_reader = easyocr.Reader(["ar", "en"], gpu=False)
    return latin_reader, arabic_reader


def run_easyocr(reader, image_path: str) -> str:
    if reader is None:
        return ""
    try:
        lines = reader.readtext(image_path, detail=0, paragraph=True)
        return " ".join(lines).strip()
    except Exception as e:  # noqa: BLE001 - spike: report any failure verbatim
        return f"[error: {e}]"


def build_tifinagh_client(space_id: str):
    try:
        from gradio_client import Client
    except ImportError:
        print("[spike] gradio_client not installed -> skipping Tifinagh. "
              "pip install gradio_client")
        return None
    try:
        print(f"[spike] Connecting to Tifinagh Space: {space_id} ...")
        token = os.getenv("HUGGINGFACE_API_KEY")
        return Client(space_id, token=token)
    except Exception as e:  # noqa: BLE001
        print(f"[spike] Could not connect to Tifinagh Space: {e}")
        return None


def run_tifinagh(client, api_name: str, image_path: str) -> str:
    if client is None:
        return ""
    try:
        from gradio_client import handle_file
        result = client.predict(handle_file(image_path), api_name=api_name)
        return str(result).strip()
    except Exception as e:  # noqa: BLE001
        return f"[error: {e}  (try a different --tifinagh-api; see the Space's 'Use via API')]"


def _img_data_uri(path: str) -> str:
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def write_report(rows, meta: dict):
    os.makedirs(OUT_DIR, exist_ok=True)
    report_path = os.path.join(OUT_DIR, "report.html")
    parts = [
        "<!doctype html><meta charset='utf-8'>",
        "<title>OCR Spike Report</title>",
        "<style>",
        "body{font-family:system-ui,Arial,sans-serif;margin:24px;background:#fafafa}",
        "table{border-collapse:collapse;width:100%}",
        "td,th{border:1px solid #ddd;padding:8px;vertical-align:top;text-align:left}",
        "th{background:#333;color:#fff}",
        "img{max-width:420px;height:auto;display:block}",
        ".tf{font-size:20px}",  # Tifinagh renders larger for legibility
        "code{white-space:pre-wrap}",
        "</style>",
        f"<h1>OCR Phase-0 Spike</h1>",
        "<p>" + html.escape(
            f"source={meta['source']} | frames={meta['n']} | "
            f"interval={meta['interval']}s | band=bottom {int(meta['band']*100)}% | "
            f"tifinagh_space={meta['tifinagh_space']}"
        ) + "</p>",
        "<table><tr><th>t (s)</th><th>subtitle crop</th>"
        "<th>EasyOCR Latin</th><th>EasyOCR Arabic</th><th>Tifinagh</th></tr>",
    ]
    for r in rows:
        parts.append(
            "<tr>"
            f"<td>{r['t']}</td>"
            f"<td><img src='{_img_data_uri(r['path'])}'></td>"
            f"<td><code>{html.escape(r['latin'])}</code></td>"
            f"<td dir='rtl'><code>{html.escape(r['arabic'])}</code></td>"
            f"<td class='tf'><code>{html.escape(r['tifinagh'])}</code></td>"
            "</tr>"
        )
    parts.append("</table>")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print(f"\n[spike] Report written to: {os.path.abspath(report_path)}")
    print("[spike] Open it in a browser and judge each engine's accuracy.")


def main():
    ap = argparse.ArgumentParser(description="OCR Phase-0 spike for burned-in subtitles.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--video", help="Path to a local video file.")
    src.add_argument("--url", help="Video URL (downloaded with yt-dlp).")
    ap.add_argument("--interval", type=float, default=4.0,
                    help="Seconds between sampled frames (default 4).")
    ap.add_argument("--band", type=float, default=0.25,
                    help="Bottom fraction of the frame to crop as the subtitle "
                         "strip (default 0.25 = bottom 25%%).")
    ap.add_argument("--tifinagh-space", default="ayymen/Tifinagh-OCR",
                    help="HF Space id for the Tifinagh OCR model.")
    ap.add_argument("--tifinagh-api", default="/predict",
                    help="gradio api_name on the Tifinagh Space (default /predict).")
    ap.add_argument("--no-latin", action="store_true", help="Skip EasyOCR Latin.")
    ap.add_argument("--no-arabic", action="store_true", help="Skip EasyOCR Arabic.")
    ap.add_argument("--no-tifinagh", action="store_true", help="Skip the Tifinagh Space.")
    ap.add_argument("--max-frames", type=int, default=40,
                    help="Cap on number of crops to OCR (default 40).")
    args = ap.parse_args()

    work_dir = tempfile.mkdtemp(prefix="ocr_spike_")
    crop_dir = os.path.join(OUT_DIR, "crops")
    os.makedirs(crop_dir, exist_ok=True)

    try:
        video_path = args.video or download_url(args.url, work_dir)
        crops = sample_crops(video_path, args.interval, args.band, crop_dir)
        if args.max_frames and len(crops) > args.max_frames:
            print(f"[spike] Capping to first {args.max_frames} crops.")
            crops = crops[: args.max_frames]

        latin_reader, arabic_reader = build_easyocr_readers(
            enable_latin=not args.no_latin, enable_arabic=not args.no_arabic
        )
        tif_client = None if args.no_tifinagh else build_tifinagh_client(args.tifinagh_space)

        rows = []
        for i, c in enumerate(crops, 1):
            print(f"[spike] OCR {i}/{len(crops)} (t={c['t']}s) ...")
            rows.append({
                "t": c["t"],
                "path": c["path"],
                "latin": run_easyocr(latin_reader, c["path"]),
                "arabic": run_easyocr(arabic_reader, c["path"]),
                "tifinagh": run_tifinagh(tif_client, args.tifinagh_api, c["path"]),
            })

        write_report(rows, {
            "source": args.video or args.url,
            "n": len(rows),
            "interval": args.interval,
            "band": args.band,
            "tifinagh_space": "(skipped)" if args.no_tifinagh else args.tifinagh_space,
        })
    finally:
        # Keep crops/report; only clean the download temp dir.
        try:
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
