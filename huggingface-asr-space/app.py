import os
import torch
import json
import difflib
from transformers import pipeline
from fastapi import FastAPI, HTTPException, Body, UploadFile, File, Form, Request
from typing import List, Optional, Dict
import requests
import tempfile
import shutil
import librosa
from openai import OpenAI

app = FastAPI(title="Tachelhit ASR + DeepSeek Correction API")

# --- MODELS ---
_pipes = {}

def get_whisper_pipe(model_id: str = "openai/whisper-base"):
    global _pipes
    if model_id not in _pipes:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[ASR] Loading {model_id} on {device}...")
        _pipes[model_id] = pipeline(
            "automatic-speech-recognition",
            model=model_id,
            device=device,
            return_timestamps=True
        )
        print(f"[ASR] Model {model_id} loaded.")
        # Check available language tokens
        try:
            pipe = _pipes[model_id]
            lang_tokens = pipe.tokenizer.lang_code_to_id
            print(f"[ASR] Available language tokens: {list(lang_tokens.keys())}")
        except Exception as e:
            print(f"[ASR] Could not retrieve language tokens: {e}")
    return _pipes[model_id]

# --- CORRECTION LOGIC ---
def get_deepseek_client():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

def correct_with_deepseek(transcription: str, dataset: List[Dict]):
    client = get_deepseek_client()
    phrases = [p.get("t", "") for p in dataset if p.get("t")] if dataset else []
    
    # If no phrases, return original with perfect score
    if not phrases:
        print(f"[CORRECTION] No phrases provided, returning original transcription.")
        return transcription, 1.0
    
    # Try DeepSeek correction if client available
    if client:
        print(f"[CORRECTION] Attempting DeepSeek correction with {len(phrases)} reference phrases.")
        prompt = f"""
You are a Tamazight language expert. Given the rough ASR transcription: "{transcription}"
Select the most likely matching phrase from this dataset of known Tamazight phrases:
{json.dumps(phrases[:50], ensure_ascii=False)}
Always return a phrase from the dataset, even if the match is not perfect. Choose the most likely one.
Return the exact phrase and a confidence score between 0 and 1.
FORMAT:
PHRASE: <exact phrase from dataset>
SCORE: <0.0-1.0>
"""
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a Tamazight expert."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0
            )
            content = response.choices[0].message.content
            corrected = transcription
            score = 0.5
            for line in content.splitlines():
                if line.startswith("PHRASE:"): 
                    corrected = line.replace("PHRASE:", "").strip().strip('"')
                elif line.startswith("SCORE:"): 
                    try: score = float(line.replace("SCORE:", "").strip())
                    except: pass
            # Ensure we return a phrase from dataset
            if corrected != transcription and corrected in phrases:
                print(f"[CORRECTION] DeepSeek corrected to: {corrected} (score: {score})")
                return corrected, score
            # If DeepSeek didn't return a valid phrase, fall through to local matching
            else:
                print(f"[CORRECTION] DeepSeek returned phrase not in dataset, falling back to local matching.")
        except Exception as e:
            print(f"[CORRECTION ERROR] {e}")
            # Fallback to local matching
    
    # Local matching fallback: choose phrase with highest text similarity
    print(f"[CORRECTION] Using local matching with {len(phrases)} phrases.")
    best_phrase = transcription
    best_score = 0.0
    for phrase in phrases:
        # simple similarity using SequenceMatcher
        similarity = difflib.SequenceMatcher(None, transcription.lower(), phrase.lower()).ratio()
        if similarity > best_score:
            best_score = similarity
            best_phrase = phrase
    # If best_score is too low (below 0.3), maybe keep original? But we want a phrase anyway.
    # We'll return the best phrase even if low score.
    print(f"[CORRECTION] Local matching result: '{best_phrase}' (score: {best_score})")
    return best_phrase, best_score

# --- ENDPOINTS ---
@app.get("/")
def home():
    return {"status": "ASR + Correction Online"}

@app.post("/transcribe")
async def transcribe(
    request: Request,
    audio_file: Optional[UploadFile] = File(None),
):
    temp_file = None
    try:
        # 1. Manually parse parameters to handle both JSON and Form/Multipart
        content_type = request.headers.get("content-type", "")
        audio_url = None
        dataset = None
        glossary = None
        model_id = "SoufianeDahimi/whisper-small-tamazight" # Default model

        if "application/json" in content_type:
            # Case A: Backend calls with json={...}
            body = await request.json()
            audio_url = body.get("audio_url")
            dataset = body.get("dataset")
            glossary = body.get("glossary")
            model_id = body.get("model_id", model_id)
        else:
            # Case B: Backend calls with files={...} (multipart/form-data)
            form = await request.form()
            audio_url = form.get("audio_url")
            model_id = form.get("model_id", model_id)
            
            # Handle stringified JSON in form fields
            dataset_str = form.get("dataset")
            if dataset_str:
                try: dataset = json.loads(dataset_str)
                except: dataset = None
                
            glossary_str = form.get("glossary")
            if glossary_str:
                try: glossary = json.loads(glossary_str)
                except: glossary = None

        # 2. Get audio file
        if audio_file:
            print(f"[ASR] Processing uploaded file: {audio_file.filename}")
            suffix = os.path.splitext(audio_file.filename)[1] or ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                shutil.copyfileobj(audio_file.file, f)
                temp_file = f.name
        elif audio_url:
            print(f"[ASR] Downloading audio from: {audio_url}")
            response = requests.get(audio_url, timeout=30)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(response.content)
                temp_file = f.name
        else:
            raise HTTPException(status_code=400, detail="Missing audio_url or audio_file")

        # 3. Transcribe
        pipe = get_whisper_pipe(model_id) # Pass model_id here
        audio_data, sr = librosa.load(temp_file, sr=16000)
        
        print(f"[ASR] Starting inference with {model_id}...")

        # Get available language tokens from tokenizer
        try:
            available_lang_tokens = pipe.tokenizer.lang_code_to_id
            print(f"[ASR] Available language tokens: {list(available_lang_tokens.keys())}")
        except Exception as e:
            print(f"[ASR] Could not retrieve language tokens: {e}")
            available_lang_tokens = {}

        # Determine language candidates based on model
        if model_id and ("tamazight" in model_id.lower() or "tachelhit" in model_id.lower()):
            # For fine‑tuned Tamazight models, try ISO 639‑3 code "shi" (most likely supported) then fallback to "ber" then auto‑detect
            language_candidates = ["shi", "ber", None]
            print(f"[ASR] Using Tamazight‑fine‑tuned model: {model_id}, trying language candidates: {language_candidates}")
        else:
            # For generic Whisper, do NOT force unsupported codes. Use auto‑detect only.
            language_candidates = [None]
            print(f"[ASR] Using generic model: {model_id}, no language forced (auto‑detect).")
        
        # Filter candidates that are not in tokenizer (skip unsupported)
        filtered_candidates = []
        for lang in language_candidates:
            if lang is None:
                filtered_candidates.append(lang)
            elif lang in available_lang_tokens:
                filtered_candidates.append(lang)
            else:
                print(f"[ASR] Language '{lang}' not in tokenizer, skipping.")
        if not filtered_candidates:
            filtered_candidates = [None]  # fallback to auto-detect
        language_candidates = filtered_candidates
        
        asr_result = None
        last_error = None
        
        for lang in language_candidates:
            try:
                if lang is None:
                    print(f"[ASR] Trying transcription without language specification.")
                    asr_result = pipe(audio_data)
                else:
                    print(f"[ASR] Trying transcription with language: {lang}")
                    generate_kwargs = {
                        "task": "transcribe",
                        "num_beams": 5,
                        "language": lang
                    }
                    asr_result = pipe(audio_data, generate_kwargs=generate_kwargs)
                break  # success
            except Exception as pipe_err:
                last_error = pipe_err
                print(f"[ASR] Error with language '{lang}': {pipe_err}. Trying next candidate.")
                continue
        
        # Final fallback: try without any language specification
        if asr_result is None:
            try:
                print(f"[ASR] All candidates failed, attempting fallback with auto-detection.")
                asr_result = pipe(audio_data)
            except Exception as e:
                raise RuntimeError(f"Transcription failed completely. Last error: {last_error}. Fallback error: {e}")

        rough_text = asr_result.get("text", "").strip()
        print(f"[ASR] Inference successful. Text length: {len(rough_text)}")

        # 4. Correct
        corrected_text, score = correct_with_deepseek(rough_text, dataset or [])
        # Ensure we have a non-empty corrected text
        if not corrected_text or corrected_text.strip() == "":
            corrected_text = rough_text
            score = 0.0
            print(f"[ASR] Corrected text empty, falling back to rough transcription.")

        # 5. Segments (for UI if needed)
        segments = []
        if "chunks" in asr_result:
            for chunk in asr_result["chunks"]:
                ts = chunk.get("timestamp", (0.0, 0.0))
                segments.append({"start": ts[0], "end": ts[1] or ts[0]+2.0, "text": chunk.get("text", "").strip()})

        return {
            "rough_transcription": rough_text,
            "corrected_transcription": corrected_text,
            "similarity_score": score,
            "segments": segments
        }

    except HTTPException as he:
        # Don't mask HTTP exceptions (like 400)
        raise he
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"[ERROR] {error_msg}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file and os.path.exists(temp_file):
            os.unlink(temp_file)
