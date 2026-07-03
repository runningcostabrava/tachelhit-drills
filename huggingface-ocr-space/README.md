---
title: Tachelhit OCR
emoji: 🔤
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

# Tachelhit OCR Space

Reads **burned-in subtitles** (Latin + Arabic scripts) off video frame crops
for the tachelhit-drills app. The backend samples one frame per ASR segment,
crops the bottom subtitle band, and POSTs it here.

## API

`POST /ocr` — multipart with an `image` file. Returns:

```json
{"results": [{"text": "...", "confidence": 0.93, "script": "latin", "box": [[x,y],...]}]}
```

Results are in reading order (top-to-bottom, left-to-right).

## Deploying

Create a Docker Space and push this directory to it, then set
`HUGGINGFACE_OCR_SPACE_URL` on the backend (Render) to the Space URL.

## Scope

- Latin (Tachelhit romanization, French, Spanish, English) — EasyOCR
- Arabic — EasyOCR
- **Tifinagh — not yet**: pending the Phase-0 spike in
  `docs/OCR_FEATURE_SCOPE.md` (only research-grade models exist).
