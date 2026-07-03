"""
Tachelhit OCR Space — reads burned-in subtitles (Latin + Arabic scripts) off
video frame crops sent by the backend's /video-analysis/ocr endpoint.
Docker FastAPI service, mirrors huggingface-asr-space.

POST /ocr with an image file -> {"results": [{"text", "confidence", "script", "box"}]}

Tifinagh is NOT handled here yet — see docs/OCR_FEATURE_SCOPE.md in the main
repo (Phase-0 spike pending; only research-grade models exist for it).
"""
import io

import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile

import easyocr

app = FastAPI(title="Tachelhit OCR")

# EasyOCR's language-compatibility rules force two readers: Arabic only
# combines with English, while Latin languages combine freely.
print("[OCR] Loading EasyOCR models...")
latin_reader = easyocr.Reader(['en', 'fr', 'es'], gpu=False)
arabic_reader = easyocr.Reader(['ar', 'en'], gpu=False)
print("[OCR] Models ready.")


@app.get("/")
def root():
    return {"status": "ok", "service": "tachelhit-ocr", "scripts": ["latin", "arabic"]}


@app.post("/ocr")
async def ocr_image(image: UploadFile = File(...)):
    data = await image.read()
    img = Image.open(io.BytesIO(data)).convert("RGB")
    arr = np.array(img)

    results = []
    seen = set()
    for script, reader in (("latin", latin_reader), ("arabic", arabic_reader)):
        for box, text, conf in reader.readtext(arr):
            text = (text or "").strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:  # both readers detect Latin; keep one copy
                continue
            seen.add(key)
            results.append({
                "text": text,
                "confidence": round(float(conf), 3),
                "script": script,
                "box": [[int(x), int(y)] for x, y in box],
            })

    # Reading order (top-to-bottom, then left-to-right), so the caller can
    # join texts into a sentence
    results.sort(key=lambda r: (r["box"][0][1], r["box"][0][0]))
    return {"results": results}
