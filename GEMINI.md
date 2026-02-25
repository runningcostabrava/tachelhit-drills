# GEMINI.md - Project Context & Architectural Mandates

This file serves as the persistent memory and source of truth for Gemini CLI and other AI agents working on the **Tachelhit Drills** project.

## 🎯 Current Project Goal
Integrate an online Tamazight Speech-to-Text (ASR) system with a semantic correction layer using DeepSeek and a user-curated dataset of known phrases.

## 🏗️ Technical Architecture (ASR + Correction)

### 1. Acoustic Layer (ASR)
- **Model**: `openai/whisper-tiny` (selected for CPU efficiency on Render).
- **Service**: `backend/asr_service.py`.
- **Function**: Converts raw audio (Cloudinary/Local) into "rough" text. It handles Tamazight phonetics but may have spelling or dialect inconsistencies.

### 2. Semantic Correction Layer (DeepSeek)
- **API**: DeepSeek Chat (OpenAI-compatible SDK).
- **Service**: `backend/correction_service.py`.
- **Strategy**: "Smart Autocorrect". It takes the rough Whisper output and matches it against a controlled list of Tachelhit phrases.
- **Data Source**: Drills marked with `is_correction_dataset = True`.

### 3. Audio Trimming
- **Service**: `backend/main.py` (endpoint `/drills/{id}/trim-audio`).
- **Engine**: MoviePy.
- **Workflow**: Allows users to fix "dead air" at the start/end of recordings directly from the UI.

## 📊 Data Schema Changes
- `Drill.is_correction_dataset` (Boolean): Flag to include a drill's Tachelhit text in the DeepSeek correction phrase list.

## 🚀 Key Endpoints
- `POST /transcribe/`: Orchestrates Whisper -> DeepSeek pipeline.
- `GET /pairs/`: Lists all active dataset phrases.
- `POST /evaluate-dataset/`: WER/Accuracy diagnostic tool.

## 🛠️ Development Mandates
- **CPU First**: Always prioritize `whisper-tiny` or `whisper-base` to avoid OOM (Out Of Memory) errors on Render.
- **Dataset Integrity**: The correction layer is only as good as the `is_correction_dataset` drills. Encourage users to mark high-quality recordings.
- **Security**: Never log `DEEPSEEK_API_KEY`.

## 📂 File Map (ASR Specific)
- `backend/asr_service.py`: Whisper logic.
- `backend/correction_service.py`: DeepSeek logic.
- `backend/test_asr_correction.py`: Integration tests.
- `frontend/src/components/DrillCard.tsx`: UI for trimming and dataset selection.
