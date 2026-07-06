---
title: Tachelhit NLP Service
emoji: 🗣️
colorFrom: indigo
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# Tachelhit NLP Service — ASR + translation + OCR in one Space

One free-tier Space instead of three, so the app stops fighting the CPU quota.
Models are **lazy-loaded** on first use (fast cold start; memory only grows for
what you call).

## Endpoints
- `POST /transcribe` — `audio_file` (multipart) → `{rough_transcription, corrected_transcription, similarity_score, segments}` · `SoufianeDahimi/whisper-small-tamazight`
- `POST /translate` — JSON `{text, src_lang, tgt_lang}` → `{translation, tifinagh, latin}` · `Tamazight-NLP/NLLB-200-600M-Tamazight-All-Data-3-epoch`
- `POST /ocr` — `image` (multipart) → `{results: [{text, confidence, script, box}]}` · EasyOCR (latin + arabic)
- `GET /health`
- Gradio UI at `/` with `api_name` **predict** (audio→text) and **translate**.

## Required secret
The NLLB model is gated under the `Tamazight-NLP` org, so set a Space **secret**:
`HF_TOKEN` = a HuggingFace read token that has access to that model.

## Optional env
`ASR_MODEL_ID`, `NLLB_MODEL_ID`, `ASR_CHUNK_LENGTH_S`, `ASR_STRIDE_LENGTH_S`.
