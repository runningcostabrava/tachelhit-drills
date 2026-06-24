---
title: Tachelhit ASR Correction Service
emoji: 🎤
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Tachelhit ASR + Segmentation Service

This space provides a Whisper-based ASR service optimized for Tachelhit.
- **Models:** `openai/whisper-base` (default), `SoufianeDahimi/whisper-small-tamazight`
- **Output:** JSON segments with timestamps, with DeepSeek correction.
- **Usage:** Pass `model_id` in the API call to select the model.
- **Port:** 7860
