# OCR Feature Scope — Read on-screen text from video → drills

Status: **Scoping / Phase-0 spike**
Last updated: 2026-06-24

## 1. Goal

Let the video-to-drills pipeline read **burned-in subtitles** off a video and
turn them into drill text, in **Latin (Tachelhit romanization), Arabic, and
Tifinagh** ⵜⵉⴼⵉⵏⴰⵖ. This complements the audio path (ASR) by capturing text the
speaker never says aloud but that appears on screen.

### Decisions locked in
- **Text source:** burned-in subtitles only (not scene text, not document photos).
- **Scripts:** Latin + Arabic + Tifinagh.
- **Tifinagh approach:** run a Phase-0 spike before committing to a model.

### Why "burned-in subtitles" makes this tractable
Burned-in captions are horizontal, clean, sit in a fixed band (usually the
bottom ~20–25% of the frame), and persist for several seconds. Consequences:
- **Detection is easy** — crop a configurable bottom band instead of running a
  full scene-text detector. Faster and far more accurate on HF free-tier CPU.
- **Free dedup** — the same subtitle spans many frames; sample a few frames per
  segment and collapse identical text → one drill per subtitle, not per frame.
- **Natural alignment** — each subtitle maps to a time range that slots into the
  existing segment → drill flow.

## 2. Feasibility (verified June 2026)

| Script | Tooling reality |
|---|---|
| Latin (Tachelhit) | Solved — EasyOCR / Tesseract / PaddleOCR all read Latin well. |
| Arabic | Well-supported by EasyOCR (`ar`) and Tesseract (`ara`). |
| Tifinagh | **Research-grade.** Not in EasyOCR/PaddleOCR/standard Tesseract, but a real ecosystem exists: the `ayymen/Tifinagh-OCR` HF Space, the `Tamazight/Tifinagh-OCR-39K` dataset, CNN / CNN-Transformer models (TifinNet, AMHCD), and Tesseract-calibration papers. Most of it targets **clean printed/handwritten characters**, not arbitrary video scene-text — which is exactly why we restrict scope to clean burned-in captions. |

**Headline:** Latin + Arabic from clean captions is straightforward. Tifinagh is
feasible *for clean printed text* but needs a dedicated model; the spike decides
whether today's off-the-shelf model is good enough on real footage.

### Reference links
- Dataset: https://huggingface.co/datasets/Tamazight/Tifinagh-OCR-39K
- Demo Space: https://huggingface.co/spaces/ayymen/Tifinagh-OCR
- CNN/VGG16 OCR: https://github.com/abderrazzaq-laanaoui/Machine-Learning-OCR-For-Tifinagh
- TifinNet (CNN-Transformer): https://www.researchgate.net/publication/401534131
- Tesseract for Amazigh: https://www.researchgate.net/publication/277142272
- EasyOCR: https://github.com/JaidedAI/EasyOCR

## 3. Architecture

Mirror the existing pattern — ASR, translation, and image generation are each
their own Hugging Face Space behind the FastAPI backend.

```
Frontend (VideoDrillCreator.tsx)
   │  per-segment "Extract on-screen text (OCR)" toggle; review table column
   ▼
Backend  /video-analysis/ocr   (new endpoint in backend/main.py)
   │  1. sample frames per segment, crop bottom subtitle band
   │     (reuse the save_frame logic in backend/video_utils.py:302)
   │  2. POST crops to the OCR Space
   │  3. dedup identical subtitles; (optional) transliterate Tifinagh⇄Latin
   │     via the existing NLLB Space (it already emits "Tifinagh: …/Latín: …")
   │  4. route text to drill fields; return for MANDATORY human review
   ▼
huggingface-ocr-space/  (new Gradio + FastAPI Space, mirrors huggingface-asr-space)
   • EasyOCR  → Latin + Arabic
   • Tifinagh → dedicated model (spike decides: reuse vs fine-tune)
   • returns [{box, text, script, confidence}]
```

## 4. Integration points (already in the codebase)
- **Frame extraction exists:** `backend/video_utils.py:302` `process_and_upload_segment`
  already calls `subclip.save_frame(...)`. OCR adds a multi-frame sampler.
- **Drill text fields:** `backend/models.py:15-17` — `text_catalan`,
  `text_tachelhit` (Tifinagh), `text_arabic`. **Gap:** no Latin-Tachelhit field
  → add `text_tachelhit_latin` (+ Alembic migration), or derive it by
  transliterating the Tifinagh.
- **Endpoint home:** add `/video-analysis/ocr` alongside the existing
  `/video-analysis/*` group (`backend/main.py:1562-1869`); feed results into the
  existing `create-drills` flow.
- **Frontend:** extend the segment-review table in
  `frontend/src/components/VideoDrillCreator.tsx` with an editable OCR column —
  no new page required.

## 5. Phasing

### Phase 0 — Spike (½–1 day) ← **do this first**
Tool: `local_tools/ocr_spike.py` (+ `requirements-ocr-spike.txt`).
Point it at a real video; it samples frames, crops the bottom band, runs EasyOCR
(Latin + Arabic) and the `ayymen/Tifinagh-OCR` Space, and writes an HTML report
for side-by-side eyeballing.

```
pip install -r local_tools/requirements-ocr-spike.txt
python local_tools/ocr_spike.py --video clip.mp4 --interval 4 --band 0.25
# open ocr_spike_report/report.html
```

**Exit decision:** reuse the Tifinagh Space as-is · fine-tune from the 39K
dataset · or defer Tifinagh and ship Latin+Arabic first. Latin/Arabic will
likely look production-ready straight out of the spike.

### Phase 1 — MVP (~2–4 days)
`huggingface-ocr-space/` (EasyOCR, Latin+Arabic) + `/video-analysis/ocr` +
review-column UI. Midpoint frame only. Human review mandatory.

### Phase 2 — Tifinagh (~3–7 days, gated by Phase 0)
Integrate/fine-tune the Tifinagh model; add `text_tachelhit_latin` + migration +
Tifinagh⇄Latin transliteration via the NLLB Space.

### Phase 3 — Robustness (~3–5 days)
Multi-frame sampling + subtitle dedup; confidence thresholds; optional
scene-text detection if needed later.

**Rough total:** ~2–3 weeks for solid Latin+Arabic+printed-Tifinagh, assuming
Phase 0 shows Tifinagh-from-video is workable. Latin+Arabic-only MVP ≈ 3–4 days.

## 6. Risks
- **Tifinagh accuracy on video frames** — the dominant unknown; Phase 0 resolves it.
- **HF free-tier CPU** — OCR detection models are heavier than the ASR
  Whisper-small; cold starts + per-frame latency may push toward batching or a
  paid tier.
- **Quality floor** — OCR output must pass human review before becoming drills;
  never auto-commit.
- **Cost/perf** — frames × segments × (detect + recognize) adds up; subtitle
  dedup is essential.

## 7. Open questions for later phases
- Add `text_tachelhit_latin` column, or store only Tifinagh and transliterate on read?
- Confidence threshold below which a segment is flagged rather than pre-filled?
- Should OCR text auto-merge with ASR text for the same segment, or stay separate
  fields the user reconciles?
