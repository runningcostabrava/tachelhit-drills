---
title: Tachelhit ASR + Alignment Service
emoji: 🎤
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Tachelhit ASR + forced-alignment service

- **Model:** `ayymen/stt_zgh_fastconformer_ctc_small` (NeMo FastConformer CTC trained on
  Common Voice Standard Moroccan Tamazight, CC BY 4.0, 51 MB). Writes **Tifinagh**.
- **`POST /transcribe`** (`audio_file`) → `{"text", "segments": [{start, end, text}], "confidence"}`.
  `confidence` és el número del model (NeMo CTC): la suma de log-probabilitats del camí que ha
  triat, feta mitjana per caràcter i tornada a probabilitat amb `exp()`. Va de 0 a 1 i pot ser
  `null` quan el model no el dona — mai inventat. Serveix per ordenar la cua de confirmació:
  una frase amb certesa alta també pot ser errònia, i per això continua sent una proposta.
  Segments
  come from forced alignment of the model's own transcript, split at pauses.
- **`POST /align`** (`audio_file`, `text`, `split_on_newline`) → `{"text", "segments": [{start,
  end, text, words}], "words"}`. Give it the known text (lyrics, lesson lines, subtitles) and
  it returns when each line and each word is spoken. Lines separated by newlines (or `|`).
- Gradio API (`gradio_client`): `api_name="/predict"` (audio → text), `api_name="/align"`.
- **Port:** 7860. One request at a time (CPU).

Alignment code: `align.py` + `utils/` are NVIDIA NeMo's `tools/nemo_forced_aligner`
(Apache 2.0), as used by the `Tamazight-NLP/NeMo-Forced-Aligner` Space.

History: until 2026-10-19 this Space ran `SoufianeDahimi/whisper-small-tamazight`, a
speech→Arabic-script model (CER 0.7 on our clips, hallucinated other languages).
