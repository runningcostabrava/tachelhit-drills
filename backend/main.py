# INFO: Project: Tachelhit Drills. Feature: ASR, Correction, Translation, Video Processing. Status: Active.
import asyncio
import threading
import os
import sys
import glob
import subprocess
import json
import traceback
import tempfile
import shutil
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import quote
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Body, Form, BackgroundTasks, Request, Response
from fastapi.encoders import jsonable_encoder
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Tuple
import hashlib
import re
import secrets
from illustrate import generate_illustration, illustration_available
from draft_check import check_draft_meaning, draft_status
import lexicon
from tts_text import tts_text, VOICE_VERSION
import topics as topics_catalog
import grammar as grammar_course
import practice_steps
import method as method_mod
import practice as practice_mod
import stories as stories_mod
import night_asr
import word_audio
import transliteration
from gemini_client import gemini_generate, gemini_available, gemini_agent, BudgetExceeded
import gemini_client
import ai_budget
import dialect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, false as sa_false, func as sa_func
from sqlalchemy.orm import sessionmaker, Session
import requests
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

# El que NO es carrega en arrencar.
#
# El servei gratuït s'adorm als 15 minuts, de manera que cada visita desperta un servidor nou i
# qui obre l'app paga l'arrencada sencera. Importar-ho tot d'entrada costava 18 segons, i 13
# eren llibreries que la immensa majoria de peticions no toquen mai: moviepy i yt-dlp (vídeo),
# el client d'OpenAI (correcció) i el de Gradio (els Spaces de Hugging Face).
#
# Aquesta funció manté el nom i difereix el mòdul: les crides no canvien, i el mòdul de debò
# s'importa la primera vegada que algú el fa servir. La primera petició de vídeo paga els seus
# segons; la resta, cap.
def _lazy(module: str, name: str):
    def call(*args, **kwargs):
        import importlib
        return getattr(importlib.import_module(module), name)(*args, **kwargs)
    call.__name__ = name
    return call


Client = _lazy("gradio_client", "Client")
handle_file = _lazy("gradio_client", "handle_file")

from deep_translator import GoogleTranslator

# Load environment variables
load_dotenv()
# Console output must never break a pipeline step: on Windows a redirected stdout defaults to
# cp1252 and print() of «ɣ» raised UnicodeEncodeError inside lesson_audio_vocabulary (local
# capture backend, 2026-10-19), which the caller took as "the listening failed".
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
# Our own ASR Space (NeMo Tifinagh model + /transcribe + /align, huggingface-asr-space/). The
# Tamazight-NLP/ASR Space it used to default to is Gradio-only: no /transcribe route (404).
ASR_SPACE_DEFAULT = "https://huggingface.co/spaces/josepabloucr/huggingface-asr-space"

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

from models import Base, Drill as DrillModel, Test as TestModel, TestAttempt as TestAttemptModel, YouTubeShort as YouTubeShortModel, VideoProcessingJob as VideoProcessingJobModel, VideoSegment as VideoSegmentModel, GlossaryItem as GlossaryItemModel, DrillReview as DrillReviewModel, User as UserModel, ReviewLog as ReviewLogModel, Recording as RecordingModel, LessonProposal as LessonProposalModel, AppSetting as AppSettingModel, CaptureRequest as CaptureRequestModel, DrillTombstone as DrillTombstoneModel, UserSession as UserSessionModel, GeminiUsage as GeminiUsageModel  # ← Alias for ORM models
from schemas import DrillCreate, DrillUpdate, Drill, TestCreate, TestUpdate, Test, TestAttemptCreate, TestAttempt, YouTubeShortCreate, YouTubeShort, VideoProcessingJobCreate, VideoProcessingJob, VideoSegmentCreate, VideoSegment, TranscribeRequest, TranscribeResponse, TranslateRequest, TranslateResponse, DrillPairInfo, GlossaryItem, GlossaryItemCreate, SrtImportRequest, SrtImportResponse, SrtSegment, BulkVideoUrlUpdateRequest, BulkVideoUrlUpdateResponse, iso_z  # ← Pydantic schemas
from srt_parser import parse_srt_content, create_youtube_url_with_timestamp

def normalize_media_url(url: str) -> str:
    """
    Ensure URL has correct protocol (https:// or http://).
    If it starts with https// or http//, replace with proper colon.
    Also remove any accidental API_BASE prefix before https//.
    """
    # Función corregida para evitar corrupción de URLs Cloudinary - commit actual
    if not url:
        return url

    # 1. Fix malformed protocol (global replace) - do this first
    url = url.replace("https//", "https://").replace("http//", "http://")

    # 2. Remove API_BASE prefix if present (with or without protocol)
    prefixes_to_remove = [
        "https://tachelhit-drills-api.onrender.com",
        "http://tachelhit-drills-api.onrender.com",
        "tachelhit-drills-api.onrender.com",
    ]
    for prefix in prefixes_to_remove:
        if url.startswith(prefix):
            url = url[len(prefix):]
            break

    # 3. Si después de quitar prefijos es una URL de Cloudinary correctamente formada, NO LA TOQUIS
    if "res.cloudinary.com" in url and url.startswith("http"):
        # Ya es válida, retornar sin más cambios
        return url

    # 4. Ensure protocol for double slash
    if url.startswith("//"):
        url = "https:" + url

    # Return as is (could be relative path, absolute URL, etc.)
    return url

# Translators
translator_ca_to_ar =  GoogleTranslator(source='ca', target='ar')
translator_ca_to_en = GoogleTranslator(source='ca', target='en')

# HF Translation
HF_TRANSLATION_MODEL = os.getenv("HF_TRANSLATION_MODEL", "facebook/nllb-200-distilled-600M")
HF_TRANSLATION_SPACE_DEFAULT = "https://huggingface.co/spaces/josepabloucr/Finetuned-Quantized-NLLB"
HUGGINGFACE_TRANSLATION_SPACE_URL = os.getenv("HUGGINGFACE_TRANSLATION_SPACE_URL", HF_TRANSLATION_SPACE_DEFAULT)
# Configured (non-default) Spaces that turned out deleted/unreachable — cached so
# a dead env var doesn't make EVERY translation retry it (which crippled speed).
_dead_translation_spaces = set()
# TTS (read Tachelhit/Tifinagh text aloud). Configurable like ASR/translation so
# it can point at your own Space instead of the hardcoded upstream one. Accepts
# either a "user/space" id or a full huggingface.co/spaces URL.
HUGGINGFACE_TTS_SPACE_URL = os.getenv("HUGGINGFACE_TTS_SPACE_URL", "Tamazight-NLP/TTS")
LANGUAGE_CODE_MAP = {
    "ca": "Catalan",
    "cat": "Catalan",
    "shi": "Tachelhit/Central Atlas Tamazight",
    "ber": "Tachelhit/Central Atlas Tamazight",
    "tam": "Standard Moroccan Tamazight",
    "zgh": "Standard Moroccan Tamazight",
    "ar": "Modern Standard Arabic",
    "arb": "Modern Standard Arabic",
    "en": "English",
    "eng": "English",
    "fr": "French",
    "fra": "French",
    "es": "Spanish",
    "spa": "Spanish",
}

def translate_with_hf(text: str, src_lang: str = "Catalan", tgt_lang: str = "Tachelhit/Central Atlas Tamazight") -> str:
    """
    Translate text using our Gradio Hugging Face Space.
    """
    from gradio_client import Client

    # Try the configured Space, then the built-in default Space, so a deleted or
    # renamed configured Space auto-falls-back to a working one instead of
    # silently breaking translation (as happened when tamazight-translation-space
    # was deleted but the env var still pointed at it).
    candidates = []
    if HUGGINGFACE_TRANSLATION_SPACE_URL and HUGGINGFACE_TRANSLATION_SPACE_URL not in _dead_translation_spaces:
        candidates.append(HUGGINGFACE_TRANSLATION_SPACE_URL)
    if HF_TRANSLATION_SPACE_DEFAULT not in candidates:
        candidates.append(HF_TRANSLATION_SPACE_DEFAULT)

    for idx, space in enumerate(candidates):
        try:
            # Remove /translate suffix if present as Client expects the base URL
            space_url = space.split('/translate')[0].rstrip('/')
            note = " (default fallback)" if idx > 0 else ""
            print(f"[TRANSLATE] Connecting to Gradio Space{note}: {space_url}")

            # hf_predict waits out cold-boot and retries with a pause between
            # attempts (a sleeping free-tier Space needs time to wake)
            result = hf_predict(
                space_url,
                text, src_lang, tgt_lang, 237, 4, 1.0,
                api_name="/predict"
            )

            translation = str(result).strip()
            # An empty result means the Space answered but produced nothing —
            # treat as failure so the caller can fall back rather than storing ""
            if not translation:
                raise ValueError("Translation Space returned an empty result")
            print(f"[TRANSLATE] Success (Gradio Space{note}): '{text[:30]}...' -> '{translation[:30]}...'")
            return translation

        except Exception as e:
            print(f"[TRANSLATE] Space {space} failed: {e}")
            # remember a dead CONFIGURED space so later calls skip straight to
            # the default (never cache the default itself — it may be transient)
            if space != HF_TRANSLATION_SPACE_DEFAULT:
                _dead_translation_spaces.add(space)
            if idx < len(candidates) - 1:
                print("[TRANSLATE] Trying the default Space next.")
            else:
                import traceback
                traceback.print_exc()
                print("[TRANSLATE] All Spaces failed; falling back to Inference API.")

    # Fallback to Inference API
    api_token = os.getenv("HUGGINGFACE_API_KEY")
    if not api_token:
        print("[TRANSLATE] No HF API key for fallback. Returning original text.")
        return text

    try:
        # Map friendly names to NLLB BCP-47 codes
        nllb_code_map = {
            "Catalan": "cat_Latn",
            "Tachelhit/Central Atlas Tamazight": "zgh_Tfng",
            "Standard Moroccan Tamazight": "zgh_Tfng",
            "Modern Standard Arabic": "arb_Arab",
            "English": "eng_Latn",
            "French": "fra_Latn",
            "Spanish": "spa_Latn",
        }
        nllb_src = nllb_code_map.get(src_lang, src_lang)
        nllb_tgt = nllb_code_map.get(tgt_lang, tgt_lang)

        # Using a reliable fallback model if the custom one is down
        model_id = "facebook/nllb-200-distilled-600M"
        api_url = f"https://router.huggingface.co/hf-inference/models/{model_id}"
        headers = {"Authorization": f"Bearer {api_token}"}
        payload = {
            "inputs": text,
            "parameters": {"src_lang": nllb_src, "tgt_lang": nllb_tgt}
        }

        print(f"[TRANSLATE] Calling Inference API: {api_url}")
        response = requests.post(api_url, headers=headers, json=payload, timeout=20)
        # NLLB inference API can be slow or return 503 while loading
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                translated = result[0].get("translation_text", text)
                print(f"[TRANSLATE] Inference API Success: {translated}")
                return translated

        print(f"[TRANSLATE] Inference API returned {response.status_code}: {response.text}. Returning original.")
        return text
    except Exception as e:
        print(f"[TRANSLATE] Fallback error: {e}")
        import traceback
        traceback.print_exc()
        return text

# Config
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///drills.db")
# Usar el nuevo Space tachelhit-video-generator
HUGGINGFACE_SPACE_URL = os.getenv("HUGGINGFACE_SPACE_URL")
HUGGINGFACE_IMAGE_SPACE_URL = os.getenv("HUGGINGFACE_IMAGE_SPACE_URL", HUGGINGFACE_SPACE_URL)
space_url = os.getenv("HUGGINGFACE_SPACE_URL")
MEDIA_ROOT = "media"
os.makedirs(f"{MEDIA_ROOT}/audio", exist_ok=True)
os.makedirs(f"{MEDIA_ROOT}/video", exist_ok=True)
os.makedirs(f"{MEDIA_ROOT}/images", exist_ok=True)
os.makedirs(f"{MEDIA_ROOT}/tts", exist_ok=True)

# TTS function
def generate_catalan_tts(text: str, drill_id: int) -> str:
    """
    Generate Catalan TTS audio file and return the URL path.
    """
    try:
        from gtts import gTTS

        # Create TTS object
        tts = gTTS(text=text, lang='ca', slow=False)

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            temp_path = tmp.name
            tts.save(temp_path)

        # Determine final filename and path
        timestamp = int(datetime.utcnow().timestamp())
        filename = f"tts_{drill_id}_{timestamp}.mp3"

        # Check if Cloudinary is configured
        use_cloudinary = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))

        if use_cloudinary:
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                temp_path,
                folder="tachelhit/tts",
                public_id=f"tts_{drill_id}_{timestamp}",
                resource_type="video"  # Cloudinary treats audio as video
            )
            url = result['secure_url']
        else:
            # Save locally
            dir_path = os.path.join(MEDIA_ROOT, "tts")
            os.makedirs(dir_path, exist_ok=True)
            final_path = os.path.join(dir_path, filename)
            shutil.move(temp_path, final_path)
            url = f"/media/tts/{filename}"

        url = normalize_media_url(url)

        # Clean up temp file if it still exists
        if os.path.exists(temp_path):
            os.unlink(temp_path)

        return url
    except Exception as e:
        print(f"[TTS] Error generating TTS: {e}")
        raise

_hf_clients: Dict[str, Any] = {}


def hf_predict(space_id: str, *args, api_name: str = "/predict", token: str = None,
               retries: int = 3, timeout: float = 180.0, **kwargs):
    """
    Call a Gradio Space's predict with a generous timeout and automatic retries.
    Free-tier Spaces spin down when idle and cold-boot on the next call — the
    first attempt wakes the Space (and may time out), later attempts succeed.
    Raises the last error only if every attempt fails.
    """
    import httpx
    import time as _time
    token = token or os.getenv("HUGGINGFACE_API_KEY")
    if "huggingface.co/spaces/" in space_id:
        space_id = space_id.split("huggingface.co/spaces/")[-1].strip("/")
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            # Reuse the Gradio client per Space: building one costs a config
            # round-trip (~5 s) and a 170-cue story paid it on every call.
            client = _hf_clients.get(space_id)
            if client is None:
                client = Client(space_id, token=token,
                                httpx_kwargs={"timeout": httpx.Timeout(timeout, connect=30.0)})
                _hf_clients[space_id] = client
            # predict() streams the Space's queue over SSE, so a stuck queue keeps the
            # connection alive and the read timeout never fires. submit() + result(timeout)
            # is a wall-clock bound: on expiry the attempt fails instead of waiting forever.
            job = client.submit(*args, api_name=api_name, **kwargs)
            try:
                return job.result(timeout=timeout)
            except Exception:
                try:
                    job.cancel()
                except Exception:
                    pass
                raise
        except Exception as e:
            last_err = e
            _hf_clients.pop(space_id, None)  # a stale client after a cold restart: rebuild next time
            print(f"[HF] {space_id} attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                _time.sleep(min(20, 5 * attempt))  # give the Space time to finish booting
    raise last_err

def generate_tachelhit_tts_hf(text: str, drill_id: int) -> str:
    """
    Generate Tachelhit TTS using a Hugging Face Space (HUGGINGFACE_TTS_SPACE_URL,
    default Tamazight-NLP/TTS).
    """
    try:
        print(f"[TACHELHIT TTS] Using Space: {HUGGINGFACE_TTS_SPACE_URL}")
        # predict(text, variant, speaker, split_sentences, speaker_wav, voice_cv_model, api_name="/predict")
        result_path = hf_predict(
            HUGGINGFACE_TTS_SPACE_URL,
            text,
            "shi",
            "yan",
            False,
            None,
            "freevc24",
            api_name="/predict"
        )
        
        timestamp = int(datetime.utcnow().timestamp())
        filename = f"tachelhit_tts_{VOICE_VERSION}_{drill_id}_{timestamp}.wav"
        
        use_cloudinary = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))
        
        if use_cloudinary:
            result = cloudinary.uploader.upload(
                result_path,
                folder="tachelhit/tts",
                public_id=f"tachelhit_tts_{VOICE_VERSION}_{drill_id}_{timestamp}",
                resource_type="video"
            )
            url = result['secure_url']
        else:
            dir_path = os.path.join(MEDIA_ROOT, "tts")
            os.makedirs(dir_path, exist_ok=True)
            final_path = os.path.join(dir_path, filename)
            shutil.move(result_path, final_path)
            url = f"/media/tts/{filename}"
            
        return normalize_media_url(url)
    except Exception as e:
        print(f"[TACHELHIT TTS] Error: {e}")
        import traceback
        traceback.print_exc()
        raise

# Database configuration - handle both SQLite and PostgreSQL
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL (from Render or other services)
    # pool_pre_ping revalidates pooled connections; Render's Postgres proxy
    # drops idle ones, which otherwise 500s the first request after idle.
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)

SessionLocal = sessionmaker(bind=engine)

# Gemini usage meter: monthly money budget over every call + per-person daily cap on the
# interactive features (see ai_budget.py). Attached to the client so no call escapes it.
ai_meter = ai_budget.Meter(SessionLocal, GeminiUsageModel)
gemini_client.set_meter(ai_meter)

# ---------------------------------------------------------------------------
# Auto-capture guard (P5.2): ASR on English or music sometimes yields English
# sentences or hallucinated repeats ("R.R.R.R.R…"). Such segments must never
# be saved as attested Tachelhit. Mirrors backend/tools/find_junk_drills.py.
_JUNK_REPEAT_RUN = re.compile(r"(?:\b(\w{1,3})\b[\s.,]*)(?:\1[\s.,]*){5,}", re.I)
_JUNK_ENGLISH = re.compile(r"\b(" + "the|and|you|that|this|with|have|from|they|what|about|going|actually|little|bit|bus|grab|called|can't|don't|didn't|won't|isn't|tell|i'm|i am|we are|it's|bear|fall|asleep|therefore|lost|because|would|could|should|there|here|where|when|then|than|your|their|just|like|know|think|want|need|make|take|come|some|thing|time|people|back|only|over|also|into|very|well|much|many|more|most|other|through|before|after|never|always|really|something|nothing|everything|world|life|love|heart|mind|night|every|again|please|thank|sorry|hello|goodbye" + r")\b", re.I)
_TIFINAGH_RE = re.compile(r"[\u2D30-\u2D7F]")


_TMZ_LETTERS = re.compile(r"[ɣḍḥẓṭṛṣɛƹǧčɛ\u2D30-\u2D7F]")
_EN_LETTERS = re.compile(r"[ovpe]", re.I)  # rare in Latin Tachelhit, common in English
_EN_SMALL = re.compile(
    r"\b(a|an|the|of|and|to|in|is|are|my|your|his|her|our|their|this|that|with|for|from|"
    r"animals?|birds?|horse|hen|owl|cat|dog|cow|goat|sheep|fish|water|bread|house|school|"
    r"vocabulary|vocabuary|lesson|numbers?|colou?rs?|family|mother|father|brother|sister|"
    r"hello|good|morning|night|thank|you|yes|no|one|two|three|four|five)\b", re.I)


def cue_text_for_storage(seg: Dict[str, Any]) -> str:
    """Keep a caption cue's line breaks in text_original (bilingual cues)."""
    lines = seg.get("lines") or []
    return "\n".join(lines) if len(lines) > 1 else (seg.get("text") or "")


def split_bilingual_cue(text: Optional[str]) -> Tuple[str, Optional[str], Optional[str]]:
    """Teaching videos caption one cue as `agmar` + `horse` (word + gloss).
    Returns (tachelhit_text, gloss, gloss_lang) — gloss None for ordinary cues.
    Decides by script-specific letters first, then English-likeness; on a tie
    the first line is the target language (the convention in these videos)."""
    t = (text or "").strip()
    lines = [l.strip() for l in t.split("\n") if l.strip()]

    def tmz(x: str) -> int:
        return 3 * len(_TMZ_LETTERS.findall(x))

    def en(x: str) -> int:
        return len(_EN_LETTERS.findall(x)) + 3 * len(_EN_SMALL.findall(x))

    if len(lines) == 1:
        # "I ya-ha ya-wa ! tinew a tinew da (Oh, my story ...)": the band's own line with
        # the English meaning in parentheses (Tasuta N-Imal's track is written this way).
        m = re.match(r"^(.*\S)\s*\(([^()]{3,})\)\s*$", lines[0])
        if m:
            outside, inside = m.group(1).strip(" -–—!?.,"), m.group(2).strip()
            # the parenthesis reads as English (a small English word inside) and the line
            # outside does not ('a' / 'i' are also Tachelhit, so they do not count)
            inside_en = len(_EN_SMALL.findall(inside))
            outside_en = len([w for w in _EN_SMALL.findall(outside) if w.lower() not in ("a", "i")])
            if outside and inside_en >= 1 and outside_en == 0:
                return outside, inside, "en"
    if len(lines) != 2:
        return t, None, None
    a, b = lines

    score_a = tmz(a) - en(a)   # >0 looks Tamazight, <0 looks English
    score_b = tmz(b) - en(b)
    if score_a == score_b:
        return a, b, "en"
    return (a, b, "en") if score_a > score_b else (b, a, "en")


def _gloss_key(text: str) -> str:
    """Lookup key for a translated item: no bidi/format marks, no surrounding
    punctuation, collapsed spaces, lowercase — the model drops the invisible
    RTL mark and trailing dots of Arabic subtitle cues from its JSON keys."""
    import unicodedata
    t = "".join(ch for ch in str(text or "") if unicodedata.category(ch) != "Cf")
    t = " ".join(t.split()).strip(" .…-–—:;,!?\"'«»")
    return t.lower()


def _parse_gloss_json(answer: str) -> Dict[str, Dict[str, str]]:
    """Gemini answers a JSON object {gloss: {"ca": ..., "ar": ...}}; tolerate fences."""
    m = re.search(r"\{.*\}", answer or "", re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return {}
    out: Dict[str, Dict[str, str]] = {}
    for k, v in (data.items() if isinstance(data, dict) else []):
        if isinstance(v, dict):
            out[_gloss_key(k)] = {t: str(v.get(t) or "").strip() for t in ("ca", "ar")}
    return out


def translate_glosses(glosses: List[str], src_lang: str = "English",
                      targets: Tuple[str, ...] = ("ca", "ar"), chunk: int = 40) -> Dict[str, Dict[str, str]]:
    """Catalan (+ Arabic) for a list of items — glosses ("horse") or whole caption
    sentences. Gemini in chunks of `chunk` items (a 170-sentence story blew the
    output budget in one call and silently fell back to NLLB per cue); the
    translation Space per item is the fallback."""
    uniq = [g for g in dict.fromkeys((g or "").strip() for g in glosses) if g]
    result: Dict[str, Dict[str, str]] = {}
    if not uniq:
        return result
    names = {"ca": "Catalan", "ar": "Modern Standard Arabic"}
    want = [t for t in targets if t in names and names[t] != src_lang]
    if gemini_available() and want:
        tlist = " and ".join(f"{names[t]} (\"{t}\")" for t in want)
        for i in range(0, len(uniq), chunk):
            part = uniq[i:i + chunk]
            try:
                prompt = ("Translate each " + src_lang + " item into " + tlist + ". Items are words, phrases or "
                          "subtitle sentences from a language-learning video; keep number/article form and register, "
                          "lowercase single words unless proper nouns, no explanations. Answer ONLY with a JSON object "
                          "mapping each item (exactly as given) to {" + ", ".join(f"\"{t}\": ..." for t in want) + "}.\n\nItems:\n"
                          + "\n".join(f"- {g}" for g in part))
                answer = gemini_generate("You are a precise bilingual lexicographer.",
                                         [{"role": "user", "text": prompt}], max_output_tokens=8000, temperature=0.1, timeout=180)
                parsed = _parse_gloss_json(answer)
                for g in part:
                    hit = parsed.get(_gloss_key(g))
                    if hit and all(hit.get(t) for t in want):
                        result[g] = hit
                print(f"[AUTO] Gemini translated {sum(1 for g in part if g in result)}/{len(part)} items ({src_lang} -> {','.join(want)})")
            except Exception as e:
                print(f"[AUTO] Gemini batch translation failed ({e}); using the translation Space for this chunk")
    for g in uniq:
        if g in result:
            continue
        entry: Dict[str, str] = {}
        for tgt in want:
            try:
                entry[tgt] = translate_with_hf(g, src_lang, names[tgt])
            except Exception as e:
                print(f"[AUTO] Translation ({tgt}) failed for {g[:40]!r}: {e}")
        result[g] = entry
    return result


# ---------------------------------------------------------------------------
# Lesson mode (frame reading). Talking-head lessons show the letter / word on
# screen (Tifinagh and often Latin) while the teacher explains in English or
# Arabic; speech recognition of that is useless, the frames are the content.
def extract_frames(video_path: str, out_dir: str, every: float = 2.0, width: int = 640) -> List[Tuple[float, str]]:
    """One JPEG every `every` seconds -> [(second, path)]. Needs ffmpeg."""
    os.makedirs(out_dir, exist_ok=True)
    pattern = os.path.join(out_dir, "f_%05d.jpg")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", video_path,
                    "-vf", f"fps=1/{every},scale={width}:-2", "-q:v", "4", pattern],
                   check=True, capture_output=True, timeout=600)
    files = sorted(glob.glob(os.path.join(out_dir, "f_*.jpg")))
    return [(i * every, f) for i, f in enumerate(files)]


def _parse_json_object(text: str) -> Optional[dict]:
    """The first JSON object in a model answer, repairing the usual damage (code fences,
    trailing commas, an answer cut off mid-list). None when nothing parses."""
    m = re.search(r"\{.*\}", text or "", re.S)
    raw = m.group(0) if m else (text or "").strip()
    if not raw:
        return None
    candidates = [raw, re.sub(r",\s*([}\]])", r"\1", raw)]
    # cut off mid-list: close what is open after the last complete item
    cut = raw.rfind("}")
    if cut > 0:
        trimmed = raw[:cut + 1]
        opens = trimmed.count("[") - trimmed.count("]")
        braces = trimmed.count("{") - trimmed.count("}")
        candidates.append(re.sub(r",\s*([}\]])", r"\1", trimmed + "]" * max(0, opens) + "}" * max(0, braces)))
    for c in candidates:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except ValueError:
            continue
    return None


def lesson_audio_vocabulary(video_path: str, tmp_dir: str) -> Dict[str, Any]:
    """What the teacher SAYS: the letters taught and every example word with its
    meaning. Frame OCR confuses ⵖ/ⵅ and ⵏ/ⵍ; the spoken lesson is unambiguous.
    Returns {"speech_language", "letters": [{name, latin}], "words": [{latin, meaning_en}]} or {}."""
    import base64
    from gemini_client import _generate_content
    # The audio goes in LABELLED 30 s chunks: Gemini's own timestamps drift, but
    # "which chunk" is reliable, and 30 s is enough to find the word on screen.
    CHUNK = 30.0
    parts: List[Dict[str, Any]] = []
    try:
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video_path],
                               capture_output=True, text=True, timeout=60).stdout.strip()
        duration = float(probe or 0) or 600.0
        if duration > 1800:  # a 30-minute lecture is not a lesson clip
            return {}
        n = 0
        t = 0.0
        while t < duration:
            chunk = os.path.join(tmp_dir, f"lesson_audio_{n:03d}.mp3")
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t), "-t", str(CHUNK), "-i", video_path, "-vn",
                            "-ac", "1", "-ar", "16000", "-b:a", "40k", chunk], check=True, capture_output=True, timeout=600)
            with open(chunk, "rb") as fh:
                parts.append({"text": f"[audio chunk {n}: {t:.0f}s to {min(t + CHUNK, duration):.0f}s]"})
                parts.append({"inline_data": {"mime_type": "audio/mpeg", "data": base64.b64encode(fh.read()).decode()}})
            n += 1
            t += CHUNK
    except Exception as e:
        print(f"[LESSON] audio extraction failed: {e}")
        return {}
    prompt = ("These are consecutive 30-second chunks of a Tamazight (Amazigh) language lesson, each labelled with its "
              "chunk number and seconds. Identify the language the teacher speaks. List the Tifinagh letters being "
              "taught (IRCAM name such as yab, and the Latin sound) and EVERY Tamazight example word or phrase the "
              "teacher gives, spelled in academic Latin (ɣ ḍ ḥ ṭ ẓ ɛ; write 'gh' as ɣ), with the meaning in English "
              "exactly as the teacher explains it, and the chunk number in which the teacher FIRST says it. Answer ONLY "
              "with JSON {\"speech_language\": \"...\", \"letters\": [{\"name\": \"yab\", \"latin\": \"b\", \"chunk\": 1}], "
              "\"words\": [{\"latin\": \"ibba\", \"meaning_en\": \"my father\", \"chunk\": 1}]}.")
    payload = {"systemInstruction": {"parts": [{"text": "You transcribe language lessons precisely."}]},
               "contents": [{"role": "user", "parts": parts + [{"text": prompt}]}],
               "generationConfig": {"maxOutputTokens": 12000, "temperature": 0.1, "thinkingConfig": {"thinkingBudget": 0}}}
    try:
        vocab = None
        for attempt in range(2):
            out = _generate_content(payload, 300)
            text = "".join(pp.get("text", "") for pp in out["candidates"][0]["content"]["parts"])
            finish = (out.get("candidates") or [{}])[0].get("finishReason")
            if finish and finish != "STOP":
                print(f"[LESSON] audio vocabulary answer finished with {finish} ({len(text)} chars): a long lesson may be cut short")
            vocab = _parse_json_object(text)
            if vocab is not None:
                break
            print(f"[LESSON] audio vocabulary answer was not valid JSON (attempt {attempt + 1}); asking again")
            payload["contents"][0]["parts"][-1] = {"text": prompt + " Reply with STRICTLY valid JSON: no comments, no trailing commas, no text outside the object."}
        if vocab is None:
            raise ValueError("no valid JSON after 2 attempts")
        vocab["words"] = [w for w in (vocab.get("words") or []) if isinstance(w, dict) and (w.get("latin") or "").strip()]
        vocab["letters"] = [l for l in (vocab.get("letters") or []) if isinstance(l, dict) and (l.get("latin") or "").strip()]
        for item in vocab["words"] + vocab["letters"]:
            try:
                c = int(item.get("chunk"))
                item["t0"], item["t1"] = c * CHUNK, (c + 1) * CHUNK
            except (TypeError, ValueError):
                item["t0"] = item["t1"] = None
        print(f"[LESSON] audio: {vocab.get('speech_language')}; letters {[(l.get('name'), l.get('chunk')) for l in vocab['letters']]}; "
              f"words {[(w['latin'], w.get('meaning_en'), w.get('chunk')) for w in vocab['words']]}")
        return vocab
    except Exception as e:
        print(f"[LESSON] audio vocabulary failed: {e}")
        return {}


def apply_lesson_vocabulary(segs: List[Dict[str, Any]], vocab: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Reconcile frame readings with what the teacher said. Letters match by
    sound; words are ALIGNED IN ORDER with the spoken example words (the teacher
    shows them in the order he says them), scored by glyph similarity, so an OCR
    misread (ⵖ read as ⵅ) still lands on the right word. Matched spans take the
    teacher's meaning and a deterministic Tifinagh spelling; unmatched readings
    are dropped. Pure, testable."""
    import difflib
    from transliteration import to_forms
    norm = lambda k: k.translate(str.maketrans({"ɣ": "x", "n": "l", "e": "i", "ẓ": "z", "ḍ": "d", "ṭ": "t", "ḥ": "h", "ṛ": "r", "ɛ": "i"}))
    words = []
    for w in vocab.get("words") or []:
        f = to_forms(w["latin"])
        words.append({"key": f["key"], "latin": f["clean_latin"], "tifinagh": f["tifinagh"],
                      "meaning_en": (w.get("meaning_en") or "").strip(), "t0": w.get("t0"), "t1": w.get("t1")})
    letters = {}
    letter_windows = []
    for l in vocab.get("letters") or []:
        f = to_forms(l["latin"])
        letters[f["key"]] = {"latin": f["clean_latin"], "tifinagh": f["tifinagh"], "name": (l.get("name") or "").strip()}
        if l.get("t0") is not None:
            letter_windows.append((l["t0"] - 5.0, l["t1"] + 25.0))
    if not words and not letters:
        return segs
    out: List[Dict[str, Any]] = []
    word_spans: List[Dict[str, Any]] = []
    seen_letters: set = set()
    for sg in segs:
        key = to_forms(sg.get("latin") or "")["key"] if sg.get("latin") else ""
        in_letter_window = (not letter_windows) or any(lo <= sg["start"] <= hi for lo, hi in letter_windows)
        if (sg.get("kind") == "letter" or len(key) == 1) and in_letter_window:
            hit = letters.get(key)
            if hit and key not in seen_letters:  # one drill per letter taught
                seen_letters.add(key)
                out.append({**sg, "text": hit["tifinagh"], "tifinagh": hit["tifinagh"], "latin": hit["latin"],
                            "gloss": f"letter {hit['name']} ({hit['latin']})" if hit["name"] else sg.get("gloss"),
                            "gloss_lang": "en", "kind": "letter"})
            continue
        # a "letter" read outside the letter's window is usually a misread word: let the
        # window/order assignment decide
        word_spans.append({**sg, "_key": key})
    pairs = []
    if words and all(w.get("t0") is not None for w in words):
        # Time windows from the audio chunks + the order the words are taught: each
        # spoken word takes the earliest still-free on-screen span that overlaps
        # [t0 - 5, t1 + 25] and starts after the previous word's span. Glyph
        # similarity only breaks ties (frame OCR of Tifinagh is unreliable).
        taken: set = set()
        prev_end = -1.0
        for wj, w in enumerate(words):
            lo, hi = w["t0"] - 5.0, w["t1"] + 25.0
            cands = [(si, sg) for si, sg in enumerate(word_spans)
                     if si not in taken and sg["end"] >= lo and sg["start"] <= hi and sg["start"] >= prev_end]
            if not cands:
                continue
            best_sim = max(difflib.SequenceMatcher(None, norm(c[1]["_key"]), norm(w["key"])).ratio() for c in cands)
            strong = [c for c in cands if difflib.SequenceMatcher(None, norm(c[1]["_key"]), norm(w["key"])).ratio() >= max(0.6, best_sim)]
            si, sg = (strong or sorted(cands, key=lambda c: c[1]["start"]))[0]
            taken.add(si)
            prev_end = sg["end"]
            pairs.append((si, wj))
    if pairs:
        n, m = len(word_spans), len(words)
    else:
        # monotonic alignment (longest-common-subsequence style DP on similarity)
        n, m = len(word_spans), len(words)
    sim = [[difflib.SequenceMatcher(None, norm(word_spans[i]["_key"]), norm(words[j]["key"])).ratio() for j in range(m)] for i in range(n)]
    best = [[0.0] * (m + 1) for _ in range(n + 1)]
    choice = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1 if not pairs else 0):
        for j in range(1, m + 1):
            cands = [(best[i - 1][j], "skip_span"), (best[i][j - 1], "skip_word")]
            # Order carries most of the information (the teacher shows the words as he
            # says them); glyph similarity only breaks ties, so every match earns a bonus.
            cands.append((best[i - 1][j - 1] + 0.5 + sim[i - 1][j - 1], "match"))
            best[i][j], choice[i][j] = max(cands)
    if not pairs:
        i, j = n, m
        while i > 0 and j > 0:
            c = choice[i][j]
            if c == "match":
                pairs.append((i - 1, j - 1)); i -= 1; j -= 1
            elif c == "skip_span":
                i -= 1
            else:
                j -= 1
    matched_words = set()
    for si, wj in sorted(pairs):
        sg, w = word_spans[si], words[wj]
        if wj in matched_words:
            continue
        matched_words.add(wj)
        out.append({**sg, "text": w["tifinagh"], "tifinagh": w["tifinagh"], "latin": w["latin"],
                    "gloss": w["meaning_en"] or sg.get("gloss"), "gloss_lang": "en", "kind": "word"})
    for si, sg in enumerate(word_spans):
        if not any(p[0] == si for p in pairs):
            print(f"[LESSON] dropping frame reading {sg.get('latin')!r} ({sg['start']}-{sg['end']}s): not among the spoken words")
    last_end = max([x["end"] for x in out] + [0.0])
    for wj, w in enumerate(words):
        if wj not in matched_words:
            print(f"[LESSON] spoken word {w['latin']!r} ({w['meaning_en']}) was not found on screen: text-only drill")
            out.append({"start": None, "end": None, "order": last_end + 0.001 * (wj + 1), "text": w["tifinagh"],
                        "tifinagh": w["tifinagh"], "latin": w["latin"], "gloss": w["meaning_en"] or None,
                        "gloss_lang": "en" if w["meaning_en"] else None, "kind": "word", "no_media": True})
    return sorted(out, key=lambda x: x["start"] if x["start"] is not None else x["order"])


_TIFINAGH_FONTS = ["C:/Windows/Fonts/ebrima.ttf", "/usr/share/fonts/truetype/noto/NotoSansTifinagh-Regular.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"]


def render_tifinagh(text: str, path: str, size: int = 96) -> Optional[str]:
    """Render a Tifinagh string to a PNG (reference image for picture-to-picture
    matching). Returns the path or None when no Tifinagh font is available."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None
    font = None
    for f in _TIFINAGH_FONTS:
        if os.path.exists(f):
            try:
                font = ImageFont.truetype(f, size)
                break
            except Exception:
                continue
    if font is None:
        return None
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    l, t, r, b = probe.textbbox((0, 0), text, font=font)
    img = Image.new("RGB", (r - l + 60, b - t + 50), "white")
    ImageDraw.Draw(img).text((30 - l, 25 - t), text, font=font, fill=(235, 120, 20))
    img.save(path)
    return path


def _frame_choices_from_gemini(frames: List[Tuple[float, str]], options: List[Dict[str, str]],
                               ref_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Multiple choice per frame: which of the known lesson items is written on
    screen (or none). Candidates are shown as RENDERED images (the model compares
    shapes far better than it reads Tifinagh code points). Returns
    [{"t": sec, "choice": option id or "N"}]."""
    import base64
    from gemini_client import _generate_content
    parts: List[Dict[str, Any]] = [{"text": (
        "These are frames from a Tamazight language lesson, each labelled with its second. The lesson's items are "
        "listed below; each candidate is shown as a reference image of the exact same Tifinagh letters (the on-screen "
        "font differs, the letter shapes are the same).")}]
    for o in options:
        parts.append({"text": f"Candidate {o['id']}: {o['tifinagh']} (Latin {o['latin']}{', ' + o['meaning'] if o.get('meaning') else ''})"})
        ref = render_tifinagh(o["tifinagh"], os.path.join(ref_dir or tempfile.gettempdir(), f"ref_{o['id']}.png")) if ref_dir is not None else None
        if ref:
            with open(ref, "rb") as fh:
                parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(fh.read()).decode()}})
    parts.append({"text": (
        "Candidate N: none of them / no lesson text on screen.\n"
        "For EACH frame below, which ONE candidate is written on screen? Match letter by letter against the reference "
        "images; a word being written letter by letter counts as that word once its first letters match and no other "
        "candidate fits. Ignore channel names, watermarks and logos. Answer ONLY with a JSON array of "
        "{\"t\": second, \"choice\": \"A\"|\"B\"|...|\"N\"}, one object per frame.")})
    for t, path in frames:
        parts.append({"text": f"[frame t={t:.1f}s]"})
        with open(path, "rb") as fh:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(fh.read()).decode()}})
    payload = {"systemInstruction": {"parts": [{"text": "You compare Tifinagh text on screen with a short list of candidates."}]},
               "contents": [{"role": "user", "parts": parts}],
               "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}}}
    data = _generate_content(payload, 180)
    text = "".join(pp.get("text", "") for pp in data["candidates"][0]["content"]["parts"])
    m = re.search(r"\[.*\]", text, re.S)
    items = json.loads(m.group(0)) if m else []
    return [i for i in items if isinstance(i, dict)]


_TIF_RE = re.compile(r"[\u2D30-\u2D7F]")


def read_sign_text(frame_path: str, expected_latin: str = "") -> Optional[str]:
    """The Tifinagh written on ONE frame (the lesson item on the board/sign), exactly as
    written. None when nothing is readable. Used to make the screen, not the listening,
    the drill's text (owner, 2026-10-19: «why not with the letters on the screen»)."""
    if not gemini_available():
        return None
    import base64
    from gemini_client import _generate_content
    try:
        with open(frame_path, "rb") as fh:
            img = base64.b64encode(fh.read()).decode()
        hint = f" The teacher is saying something like «{expected_latin}»." if expected_latin else ""
        payload = {"systemInstruction": {"parts": [{"text": "You read Tifinagh letters exactly as written."}]},
                   "contents": [{"role": "user", "parts": [
                       {"inline_data": {"mime_type": "image/jpeg", "data": img}},
                       {"text": "Transcribe EXACTLY the Tifinagh text of the lesson item shown large on this frame (a word, a short "
                                "phrase or a single letter), letter by letter, keeping every letter as written. Ignore logos, "
                                "channel names, watermarks and any Latin, Arabic or English line. Answer with the Tifinagh "
                                "text only, or an empty line if there is no Tifinagh lesson item." + hint}]}],
                   "generationConfig": {"maxOutputTokens": 60, "temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}}}
        data = _generate_content(payload, 90)
        text = "".join(pp.get("text", "") for pp in data["candidates"][0]["content"]["parts"]).strip().strip("«»\"'")
        text = text.splitlines()[0].strip() if text else ""
        tif = len(_TIF_RE.findall(text))
        if not text or tif == 0 or len(text) > 80 or tif < 0.6 * len(text.replace(" ", "")):
            return None
        return text
    except Exception as e:
        print(f"[LESSON] sign reading failed: {e}")
        return None


def lesson_items_by_choice(frames: List[Tuple[float, str]], vocab: Dict[str, Any], every: float = 2.0,
                           batch: int = 12) -> List[Dict[str, Any]]:
    """Frames -> multiple-choice labels -> one span per lesson item (the longest run
    of frames labelled with it, inside the item's audio window when known)."""
    from transliteration import to_forms
    options: List[Dict[str, Any]] = []
    for l in vocab.get("letters") or []:
        f = to_forms(l["latin"])
        options.append({"kind": "letter", "latin": f["clean_latin"], "tifinagh": f["tifinagh"],
                        "meaning": f"letter {l.get('name')}" if l.get("name") else "", "name": l.get("name") or "",
                        "t0": l.get("t0"), "t1": l.get("t1")})
    for w in vocab.get("words") or []:
        f = to_forms(w["latin"])
        options.append({"kind": "word", "latin": f["clean_latin"], "tifinagh": f["tifinagh"],
                        "meaning": (w.get("meaning_en") or "").strip(), "t0": w.get("t0"), "t1": w.get("t1")})
    # de-duplicate by spelling
    uniq: Dict[str, Dict[str, Any]] = {}
    for o in options:
        uniq.setdefault(o["tifinagh"], o)
    options = list(uniq.values())
    for n, o in enumerate(options):
        o["id"] = chr(ord("A") + n)
    labels: Dict[float, str] = {}
    ref_dir = os.path.join(os.path.dirname(frames[0][1]) if frames else tempfile.gettempdir(), "refs")
    os.makedirs(ref_dir, exist_ok=True)
    for i in range(0, len(frames), batch):
        chunk = frames[i:i + batch]
        try:
            for c in _frame_choices_from_gemini(chunk, options, ref_dir):
                labels[round(float(c.get("t") or 0), 1)] = str(c.get("choice") or "N").strip().upper()[:1]
        except Exception as e:
            print(f"[LESSON] choice batch {i // batch} failed: {e}")
    # runs of frames with the same label -> spans
    runs: List[Dict[str, Any]] = []
    for t, _ in frames:
        lab = labels.get(round(t, 1), "N")
        if lab == "N":
            continue
        if runs and runs[-1]["id"] == lab and t - runs[-1]["end"] <= every + 0.01:
            runs[-1]["end"] = t + every
        else:
            runs.append({"id": lab, "start": t, "end": t + every})
    out: List[Dict[str, Any]] = []
    for o in options:
        mine = [r for r in runs if r["id"] == o["id"]]
        if o.get("t0") is not None:
            inside = [r for r in mine if r["end"] >= o["t0"] - 5.0 and r["start"] <= o["t1"] + 25.0]
            mine = inside or mine
        if not mine:
            print(f"[LESSON] {o['latin']!r} ({o['meaning']}) never recognised on screen: text-only drill")
            out.append({"start": None, "end": None, "order": (o.get("t0") or 0) + 0.001, "text": o["tifinagh"], "tifinagh": o["tifinagh"],
                        "latin": o["latin"], "gloss": o["meaning"] or None, "gloss_lang": "en" if o["meaning"] else None,
                        "kind": o["kind"], "no_media": True})
            continue
        best = max(mine, key=lambda r: r["end"] - r["start"])
        # The letters on the screen are the text; the heard word only chose the frames.
        tifinagh, latin = o["tifinagh"], o["latin"]
        mid = (best["start"] + best["end"]) / 2.0
        frame = min(frames, key=lambda fr: abs(fr[0] - mid))[1] if frames else None
        screen = read_sign_text(frame, o["latin"]) if frame else None
        screen_disagrees = None
        if screen:
            import difflib
            same_word = difflib.SequenceMatcher(None, to_forms(screen)["key"], to_forms(o["tifinagh"])["key"]).ratio() >= 0.7
            if same_word:
                # Same word: the board's letters are the authority (ⵥ vs ⵣ, ⴳⴳⵯ, doubled letters).
                tifinagh = screen
                latin = to_forms(screen)["clean_latin"]
            else:
                # A different reading: Gemini misreads stylised Tifinagh signs too often to
                # overrule a heard word that fits the meaning; keep it as a review hint.
                screen_disagrees = screen
                print(f"[LESSON] screen reads {screen!r} but the lesson says {o['tifinagh']!r} ({o['latin']}): keeping the heard word, flagged")
        out.append({"start": best["start"], "end": best["end"], "text": tifinagh, "tifinagh": tifinagh,
                    "latin": latin, "latin_heard": o["latin"], "screen_read": screen_disagrees,
                    "gloss": (o["meaning"] if o["kind"] == "word" else f"letter {o['name']} ({o['latin']})" if o["name"] else None),
                    "gloss_lang": "en", "kind": o["kind"]})
    return sorted(out, key=lambda x: x["start"] if x["start"] is not None else x["order"])


def _frame_items_from_gemini(frames: List[Tuple[float, str]], vocab: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Ask Gemini what vocabulary is written on each frame (batched images)."""
    import base64
    from gemini_client import _generate_content
    hint = ""
    if vocab and (vocab.get("words") or vocab.get("letters")):
        hint = (" The teacher's spoken lesson contains these items: letters " +
                ", ".join(f"{l.get('name')} ({l['latin']})" for l in vocab.get("letters") or []) + "; words " +
                ", ".join(f"{w['latin']} = {w.get('meaning_en')}" for w in vocab.get("words") or []) +
                ". The text on a frame is normally one of them (a letter, or a word, sometimes shown letter by "
                "letter while being spelled); report the matching item's Latin exactly as listed, and kind "
                "\"partial\" while a word is still incomplete.")
    parts: List[Dict[str, Any]] = [{"text": (
        "These are frames from a Tamazight (Amazigh) language lesson, each labelled with its second. "
        "For EACH frame report the vocabulary text written on screen as part of the lesson: a Tifinagh "
        "letter, a word or a short phrase, with its Latin transliteration (ɣ ḍ ḥ ṭ ẓ ɛ conventions) and "
        "English meaning if it can be read or inferred from the frame. Write the tifinagh field with REAL "
        "Tifinagh code points (U+2D30–U+2D7F), never Greek or Latin look-alikes (the letter that looks like Θ "
        "is ⴱ yab, Ɛ is ⵄ yaɛ, O is ⵔ yar, X is ⵅ yax, E is ⵉ yai). For a single letter put its IRCAM name in "
        "meaning_en (e.g. \"letter yab (b)\"). Ignore channel names, slogans, watermarks, social handles, "
        "logos, UI chrome and background decorations. Answer ONLY with a JSON array of "
        "objects {\"t\": second, \"kind\": \"letter\"|\"word\"|\"phrase\"|\"none\", \"tifinagh\": \"...\", "
        "\"latin\": \"...\", \"meaning_en\": \"...\"} — one object per frame, kind \"none\" when there is no lesson text." + hint)}]
    for t, path in frames:
        parts.append({"text": f"[frame t={t:.1f}s]"})
        with open(path, "rb") as fh:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(fh.read()).decode()}})
    payload = {"systemInstruction": {"parts": [{"text": "You are a careful reader of Tifinagh and Latin Amazigh text on screen."}]},
               "contents": [{"role": "user", "parts": parts}],
               "generationConfig": {"maxOutputTokens": 4000, "temperature": 0.1, "thinkingConfig": {"thinkingBudget": 0}}}
    data = _generate_content(payload, 180)
    text = "".join(pp.get("text", "") for pp in data["candidates"][0]["content"]["parts"])
    m = re.search(r"\[.*\]", text, re.S)
    items = json.loads(m.group(0)) if m else []
    return [i for i in items if isinstance(i, dict)]


_TIFINAGH_LOOKALIKES = str.maketrans({"Θ": "ⴱ", "θ": "ⴱ", "Ɛ": "ⵉ", "ɛ": "ⵉ", "O": "ⵔ", "X": "ⵅ", "Σ": "ⵙ",
                                      "E": "ⵉ", "Λ": "ⵍ", "I": "ⵏ", "C": "ⵛ", "U": "ⵓ", "H": "ⵀ", "Z": "ⵣ",
                                      "W": "ⵡ", "N": "ⴻ", "K": "ⴽ", "Q": "ⵇ", "+": "ⵜ", "V": "ⵖ", "Δ": "ⴷ"})


def _tifinagh_or_none(txt: str) -> str:
    """Gemini sometimes types Greek/Latin look-alikes for isolated Tifinagh
    letters; map them when the string has no real Tifinagh at all."""
    t = (txt or "").strip()
    if not t or _TIFINAGH_RE.search(t):
        return t
    mapped = t.translate(_TIFINAGH_LOOKALIKES)
    return mapped if _TIFINAGH_RE.search(mapped) and len(mapped) <= 3 else t


def merge_frame_items(items: List[Dict[str, Any]], every: float = 2.0, min_len: float = 1.5,
                      ignore: Optional[str] = None) -> List[Dict[str, Any]]:
    """Consecutive frames showing the same item -> one span. Returns segments
    {start, end, text, tifinagh, latin, gloss, gloss_lang, kind}. Pure, testable.
    `ignore`: the channel name — a slogan that reads like it is not a lesson item."""
    def key(i):
        return " ".join(str(i.get("tifinagh") or i.get("latin") or "").split()).lower()
    import difflib
    ign = " ".join((ignore or "").lower().replace("-", " ").split())
    spans: List[Dict[str, Any]] = []
    for i in sorted(items, key=lambda x: float(x.get("t") or 0)):
        if i.get("tifinagh"):
            i["tifinagh"] = _tifinagh_or_none(str(i["tifinagh"]))
        k = key(i)
        kind = (i.get("kind") or "none").lower()
        if kind == "none" or not k:
            continue
        if kind == "partial":
            kind = "word"  # a word being spelled out: same span as the finished word
        gloss = " ".join(str(i.get("meaning_en") or "").lower().split())
        if ign and gloss and difflib.SequenceMatcher(None, gloss, ign).ratio() >= 0.6:
            continue  # channel slogan ("Amazigh for all" ~ "Tamazight For All"), not vocabulary
        t = float(i.get("t") or 0)
        near_dup = bool(spans) and bool(spans[-1]["meaning_en"]) and spans[-1]["meaning_en"] == (i.get("meaning_en") or "") \
            and difflib.SequenceMatcher(None, spans[-1]["_key"], k).ratio() >= 0.6
        spelling = bool(spans) and (spans[-1]["_key"].startswith(k) or k.startswith(spans[-1]["_key"])) \
            and kind != "letter" and spans[-1]["kind"] != "letter"
        if spans and (spans[-1]["_key"] == k or near_dup or spelling) and t - spans[-1]["end"] <= every + 0.01:
            spans[-1]["end"] = t + every
            if spelling and len(k) > len(spans[-1]["_key"]):  # the word grew: keep the complete reading
                spans[-1]["_key"] = k
                spans[-1]["tifinagh"] = (i.get("tifinagh") or "").strip() or spans[-1]["tifinagh"]
                spans[-1]["latin"] = (i.get("latin") or "").strip() or spans[-1]["latin"]
            for f in ("latin", "meaning_en"):
                if not spans[-1].get(f) and i.get(f):
                    spans[-1][f] = i[f]
            continue
        spans.append({"_key": k, "start": t, "end": t + every, "kind": kind,
                      "tifinagh": (i.get("tifinagh") or "").strip(), "latin": (i.get("latin") or "").strip(),
                      "meaning_en": (i.get("meaning_en") or "").strip()})
    out = []
    for sp in spans:
        if sp["end"] - sp["start"] < min_len:
            sp["end"] = sp["start"] + min_len
        text = sp["tifinagh"] or sp["latin"]
        out.append({"start": round(sp["start"], 2), "end": round(sp["end"], 2), "text": text,
                    "tifinagh": sp["tifinagh"] or None, "latin": sp["latin"] or None,
                    "gloss": sp["meaning_en"] or None, "gloss_lang": "en" if sp["meaning_en"] else None,
                    "kind": sp["kind"]})
    return out


def keep_amazigh_lines(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop on-screen lines that are not Amazigh. A Darija-narrated lesson shows Arabic
    headings («الفرق بين حروف الجر»); the frame reader writes them in Tifinagh letters and
    they would become drills (batch 1 of Tamazight For All, 2026-10-19). Gemini judges the
    language of each distinct line; on any failure everything is kept (fail-open)."""
    texts = []
    for it in items:
        t = (it.get("text") or it.get("tifinagh") or it.get("latin") or "").strip()
        if t and t not in texts:
            texts.append(t)
    if not texts or not gemini_available():
        return items
    verdict: Dict[str, str] = {}
    try:
        from gemini_client import gemini_generate
        for i in range(0, len(texts), 60):
            part = texts[i:i + 60]
            prompt = ("For each line, say whether it is AMAZIGH (Tamazight/Tachelhit/Standard Moroccan Amazigh, in Tifinagh "
                      "or Latin letters; single letters and letter names count as amazigh) or ARABIC (Arabic or Moroccan "
                      "Darija, even when written in Tifinagh or Latin letters, e.g. «ⵍⴼⵔⵇ ⴱⵉⵏ ⵃⵔⵓⴼ ⵍⵊⵔ» = الفرق بين حروف الجر) "
                      "or OTHER (English, French…). Answer ONLY with a JSON object mapping the line number to "
                      "\"amazigh\" | \"arabic\" | \"other\".\n\n"
                      + "\n".join(f"{n}. {t}" for n, t in enumerate(part, 1)))
            ans = gemini_generate("You are a careful linguist of North African languages.",
                                  [{"role": "user", "text": prompt}], max_output_tokens=2000, temperature=0.0, timeout=90)
            m = re.search(r"\{.*\}", ans or "", re.S)
            data = json.loads(m.group(0)) if m else {}
            for n, t in enumerate(part, 1):
                v = str(data.get(str(n), "")).strip().lower()
                if v in ("amazigh", "arabic", "other"):
                    verdict[t] = v
    except Exception as e:
        print(f"[LESSON] language guard skipped ({e})")
        return items
    kept, dropped = [], []
    for it in items:
        t = (it.get("text") or it.get("tifinagh") or it.get("latin") or "").strip()
        if verdict.get(t) in ("arabic", "other"):
            dropped.append(t)
        else:
            kept.append(it)
    if dropped:
        print(f"[LESSON] language guard dropped {len(dropped)} non-Amazigh line(s): " + " | ".join(dropped[:5])[:300])
    return kept


def read_onscreen_vocabulary(video_path: str, tmp_dir: str, every: float = 2.0, batch: int = 12,
                             ignore: Optional[str] = None) -> List[Dict[str, Any]]:
    """Frame reading end to end: frames -> Gemini (batched) -> merged spans.
    Returns [] when Gemini is unavailable or nothing lesson-like is on screen."""
    if not gemini_available():
        return []
    vocab = lesson_audio_vocabulary(video_path, tmp_dir)
    frames = extract_frames(video_path, os.path.join(tmp_dir, "frames"), every=every)
    if vocab and (vocab.get("words") or vocab.get("letters")):
        segs = lesson_items_by_choice(frames, vocab, every=every, batch=batch)
        print(f"[LESSON] {len(frames)} frames -> {len(segs)} lesson items (multiple choice against the spoken lesson)")
        return segs
    items: List[Dict[str, Any]] = []
    for i in range(0, len(frames), batch):
        chunk = frames[i:i + batch]
        try:
            items.extend(_frame_items_from_gemini(chunk, vocab))
        except Exception as e:
            print(f"[LESSON] frame batch {i // batch} failed: {e}")
    segs = merge_frame_items(items, every=every, ignore=ignore)
    if vocab:
        segs = apply_lesson_vocabulary(segs, vocab)
    print(f"[LESSON] {len(frames)} frames -> {len(items)} readings -> {len(segs)} lesson items"
          + (" (reconciled with the spoken lesson)" if vocab else ""))
    return segs


def transcribe_narration(video_path: str, tmp_dir: str, cues: List[Dict[str, Any]], cue_lang: str = "Arabic",
                         window: float = 150.0) -> Dict[int, Dict[str, str]]:
    """Spoken Tamazight for each caption cue, anchored on the cue's text in the
    caption language so the model cannot drift. Audio is sent in windows of
    `window` seconds with the cues inside them. Returns {cue index: {"latin", "tifinagh"}}.
    Quality is a DRAFT for a speaker to confirm — Tamazight ASR is not solved."""
    import base64
    from gemini_client import _generate_content
    if not gemini_available() or not cues:
        return {}
    out: Dict[int, Dict[str, str]] = {}
    end_all = max(float(c.get("end") or 0) for c in cues)
    t0 = 0.0
    while t0 < end_all:
        t1 = min(t0 + window, end_all + 1)
        idx = [i for i, c in enumerate(cues) if c.get("start") is not None and t0 <= float(c["start"]) < t1]
        if idx:
            wav = os.path.join(tmp_dir, f"narr_{int(t0)}.mp3")
            try:
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(t0), "-t", str(t1 - t0), "-i", video_path,
                                "-vn", "-ac", "1", "-ar", "16000", "-b:a", "40k", wav], check=True, capture_output=True, timeout=300)
                with open(wav, "rb") as fh:
                    data = base64.b64encode(fh.read()).decode()
                listing = "\n".join(f"[{i}] {float(cues[i]['start']) - t0:.1f}s–{float(cues[i]['end']) - t0:.1f}s: {cues[i].get('text')}"
                                    for i in idx)
                prompt = (f"This audio is narrated in Tamazight (Amazigh). The {cue_lang} subtitles below give, for each numbered "
                          "cue, the time inside this clip and the MEANING of what is said. Transcribe what is actually SPOKEN for "
                          "each cue, in academic Latin (ɣ ḍ ḥ ṭ ẓ ɛ) and in Tifinagh; the meaning must match the subtitle. If a cue "
                          "is inaudible, give an empty string. Answer ONLY with a JSON object mapping the cue number to "
                          "{\"latin\": \"...\", \"tifinagh\": \"...\"}.\n\n" + listing)
                payload = {"systemInstruction": {"parts": [{"text": "You are a careful transcriber of Moroccan Amazigh speech."}]},
                           "contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "audio/mpeg", "data": data}}, {"text": prompt}]}],
                           "generationConfig": {"maxOutputTokens": 8000, "temperature": 0.1, "thinkingConfig": {"thinkingBudget": 0}}}
                res = _generate_content(payload, 300)
                text = "".join(pp.get("text", "") for pp in res["candidates"][0]["content"]["parts"])
                m = re.search(r"\{.*\}", text, re.S)
                parsed = json.loads(m.group(0)) if m else {}
                for k, v in parsed.items():
                    try:
                        i = int(k)
                    except ValueError:
                        continue
                    if isinstance(v, dict) and (v.get("latin") or v.get("tifinagh")):
                        out[i] = {"latin": (v.get("latin") or "").strip(), "tifinagh": (v.get("tifinagh") or "").strip()}
                print(f"[NARRATION] {t0:.0f}-{t1:.0f}s: {len([i for i in idx if i in out])}/{len(idx)} cues transcribed")
            except Exception as e:
                print(f"[NARRATION] window {t0:.0f}-{t1:.0f}s failed: {e}")
        t0 = t1
    return out


def _dialect_examples(db, variety: Optional[str], n: int = 20) -> List[str]:
    """Sentences by speakers of this variety already in the corpus (speaker-typed Latin, verified
    first), as few-shot context for the listener. Empty for unknown varieties."""
    if not variety or db is None:
        return []
    try:
        rows = (db.query(DrillModel).filter(DrillModel.variety == variety, DrillModel.text_tachelhit != None,
                                             DrillModel.text_tachelhit != "")
                .order_by(DrillModel.verified.desc().nullslast(), DrillModel.id.asc()).limit(200).all())
    except Exception:
        rows = db.query(DrillModel).filter(DrillModel.variety == variety, DrillModel.text_tachelhit != None).limit(200).all()
    out = []
    for r in rows:
        t = (r.text_tachelhit or "").strip()
        if not t or t.lower() == "text" or re.search(r"[\u2D30-\u2D7F]", t) or len(t) > 90:
            continue
        out.append(f"{t} — {r.text_catalan}" if r.text_catalan else t)
        if len(out) >= n:
            break
    return out


def _transcribe_short_clip_with_gemini(audio_url: str, variety: Optional[str] = None, meaning: Optional[str] = None,
                                       speaker_text: Optional[str] = None, examples: Optional[List[str]] = None) -> Optional[Dict[str, str]]:
    """Word/short-phrase ASR with Gemini (bake-off winner for isolated words,
    docs/ASR_BAKEOFF_2026-10-17.md). Returns {"latin", "tifinagh"} or None when
    Gemini is unavailable, the clip is longer than ASR_GEMINI_MAX_SECS, or the
    call fails (the caller then uses the Space).

    With a known variety the dialect-aware listener runs instead (dialect.py: profile of the
    variety, the corpus's own sentences, the NeMo hypothesis as a hint, dictionary candidates)."""
    if variety and dialect.profile(variety):
        try:
            out = dialect.transcribe(audio_url, variety, meaning=meaning, speaker_text=speaker_text, examples=examples,
                                     max_secs=float(os.getenv("ASR_GEMINI_MAX_SECS", "30")))
        except Exception as e:
            print(f"[ASR] dialect path failed ({e}); falling back")
            out = None
        if out:
            print(f"[ASR] {variety} via {out['engine']}: {out['latin']!r}")
            return {"latin": out["latin"], "tifinagh": out["tifinagh"]}
    if not gemini_available():
        return None
    import base64
    import tempfile as _tf
    from gemini_client import _generate_content
    try:
        max_secs = float(os.getenv("ASR_GEMINI_MAX_SECS", "20"))
        with _tf.TemporaryDirectory() as d:
            src = os.path.join(d, "clip")
            with requests.get(audio_url, timeout=120, stream=True) as r:
                r.raise_for_status()
                with open(src, "wb") as fh:
                    for chunk in r.iter_content(1 << 16):
                        fh.write(chunk)
            dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                                 capture_output=True, text=True, timeout=60).stdout.strip()
            if not dur or float(dur) > max_secs:
                return None
            wav = os.path.join(d, "clip.wav")
            # Slowed speech is heard better (bake-off round 2, docs/ASR_BAKEOFF_2026-10-19.md:
            # Gemini Flash CER 0.177 at tempo 0.85 vs 0.20 as is). ASR_GEMINI_TEMPO=1 disables.
            tempo = float(os.getenv("ASR_GEMINI_TEMPO", "0.85"))
            afilter = ["-filter:a", f"atempo={tempo}"] if 0.5 <= tempo < 1.0 else []
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", *afilter, wav],
                           check=True, capture_output=True, timeout=120)
            with open(wav, "rb") as fh:
                data = base64.b64encode(fh.read()).decode()
        payload = {"systemInstruction": {"parts": [{"text": "You transcribe Moroccan Amazigh (Tamazight/Tachelhit) speech."}]},
                   "contents": [{"role": "user", "parts": [{"inline_data": {"mime_type": "audio/wav", "data": data}},
                                                            {"text": "Transcribe exactly the Tamazight word(s) spoken, in academic Latin (ɣ ḍ ḥ ṭ ẓ ɛ). Ignore any other language. Answer with the transcription only, or an empty line if no Tamazight is spoken."}]}],
                   "generationConfig": {"maxOutputTokens": 100, "temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}}}
        out = _generate_content(payload, 120)
        latin = "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"]).strip().strip('"')
        if not latin or len(latin) > 120:
            return None
        from transliteration import to_forms
        f = to_forms(latin)
        print(f"[ASR] short clip via Gemini: {latin!r} -> {f['tifinagh']!r}")
        return {"latin": f["clean_latin"], "tifinagh": f["tifinagh"]}
    except Exception as e:
        print(f"[ASR] Gemini short-clip path failed ({e}); using the Space")
        return None


# ---------------------------------------------------------------------------
# Burned-in subtitles (songs/clips with the text painted into the picture, often
# several languages at once). Latin-script lines are read reliably by the vision
# model; Tifinagh lines are kept only when they match the Latin line's spelling.
def _subtitle_frames_from_gemini(frames: List[Tuple[float, str]]) -> List[Dict[str, Any]]:
    import base64
    from gemini_client import _generate_content
    parts: List[Dict[str, Any]] = [{"text": (
        "These are consecutive frames of a video that has SUBTITLES burned into the picture, usually in several "
        "languages at once (for example English, French, Arabic and Tachelhit/Tamazight in Latin letters, or Tifinagh). "
        "For EACH frame, transcribe exactly the subtitle lines visible, keeping each line's language. Answer ONLY with a "
        "JSON array of {\"t\": second, \"lines\": [{\"lang\": \"en\"|\"fr\"|\"ar\"|\"es\"|\"ca\"|\"shi\"|\"zgh\"|\"other\", "
        "\"text\": \"...\"}]} — one object per frame, an empty list when there is no subtitle. Use \"shi\" for Tachelhit "
        "or Tamazight written in Latin letters and \"zgh\" for Tifinagh script. Ignore channel logos, watermarks, "
        "titles and credits.")}]
    for t, path in frames:
        parts.append({"text": f"[frame t={t:.1f}s]"})
        with open(path, "rb") as fh:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(fh.read()).decode()}})
    payload = {"systemInstruction": {"parts": [{"text": "You transcribe burned-in subtitles exactly, line by line."}]},
               "contents": [{"role": "user", "parts": parts}],
               "generationConfig": {"maxOutputTokens": 6000, "temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}}}
    data = _generate_content(payload, 240)
    text = "".join(pp.get("text", "") for pp in data["candidates"][0]["content"]["parts"])
    m = re.search(r"\[.*\]", text, re.S)
    items = json.loads(m.group(0)) if m else []
    return [i for i in items if isinstance(i, dict)]


def merge_subtitle_frames(items: List[Dict[str, Any]], every: float = 1.0, min_len: float = 1.5) -> List[Dict[str, Any]]:
    """Consecutive frames with the same Tachelhit line -> one cue. Returns segments
    {start, end, text (shi Latin), tifinagh, gloss (en|fr|ar text), gloss_lang, lines}. Pure."""
    def norm(t: str) -> str:
        return " ".join((t or "").lower().replace("’", "'").split())
    cues: List[Dict[str, Any]] = []
    for i in sorted(items, key=lambda x: float(x.get("t") or 0)):
        t = float(i.get("t") or 0)
        lines = {}
        for ln in i.get("lines") or []:
            if isinstance(ln, dict) and (ln.get("text") or "").strip():
                lines.setdefault(str(ln.get("lang") or "other").lower()[:5], (ln["text"] or "").strip())
        shi = lines.get("shi") or lines.get("tzm") or ""
        if not shi and not lines.get("zgh"):
            continue
        key = norm(shi) or norm(lines.get("zgh", ""))
        if cues and cues[-1]["_key"] == key and t - cues[-1]["end"] <= every + 0.01:
            cues[-1]["end"] = t + every
            for k, v in lines.items():
                cues[-1]["lines"].setdefault(k, v)
            continue
        cues.append({"_key": key, "start": t, "end": t + every, "lines": dict(lines)})
    out = []
    import difflib
    seen_keys: List[str] = []
    # Multilingual subtitles (songs): a line with no translation under it is a title, a name
    # or credits. Amazigh-only subtitles (a text or a tale read aloud, Tifinagh alone on screen,
    # Tamazight For All): no line has a translation, and every line is the text itself — keep
    # them; the pipeline translates them afterwards.
    translated_anywhere = any(c["lines"].get(k) for c in cues for k in ("en", "fr", "ar", "es", "ca"))
    for c in cues:
        if c["end"] - c["start"] < min_len:
            continue  # a single misread frame
        # A chorus repeats: one drill per distinct line (first occurrence keeps its clip);
        # OCR spelling wobbles (lεar / l£ar / iɛar) count as the same line.
        if any(difflib.SequenceMatcher(None, c["_key"], k).ratio() >= 0.85 for k in seen_keys):
            continue
        seen_keys.append(c["_key"])
        gloss_lang = next((k for k in ("en", "fr", "ar", "es", "ca") if c["lines"].get(k)), None)
        if not gloss_lang and translated_anywhere:
            continue  # a line with no translation under it is a title, a name or credits, not a lyric
        out.append({"start": round(c["start"], 2), "end": round(c["end"], 2),
                    "text": c["lines"].get("shi") or c["lines"].get("tzm") or c["lines"].get("zgh"),
                    "latin": c["lines"].get("shi") or c["lines"].get("tzm"), "tifinagh": c["lines"].get("zgh"),
                    "gloss": c["lines"].get(gloss_lang) if gloss_lang else None, "gloss_lang": gloss_lang,
                    "lines": c["lines"], "kind": "subtitle"})
    return out


def detect_text_mode(frames: List[Tuple[float, str]]) -> str:
    """Sample a few frames and ask what kind of on-screen text the video has:
    'subtitles' (burned-in lines, usually at the bottom), 'lesson' (vocabulary / letters
    shown as teaching material), 'page' (a whole page or paragraph of Amazigh text that stays
    on screen while it is read: a text, a tale, a poem) or 'none'."""
    import base64
    from gemini_client import _generate_content
    sample = frames[:: max(1, len(frames) // 6)][:6]
    parts: List[Dict[str, Any]] = [{"text": (
        "Look at these sample frames from one video and answer with ONE word: 'subtitles' if the video has subtitle "
        "lines burned into the picture (text that changes with the speech/singing, often several languages), 'lesson' if "
        "it shows vocabulary, letters or words as teaching material, 'page' if it shows a whole page or paragraph of "
        "running text (several lines of Tifinagh or Latin Amazigh, a text or a story being read aloud), or 'none'.")}]
    for t, path in sample:
        with open(path, "rb") as fh:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(fh.read()).decode()}})
    payload = {"systemInstruction": {"parts": [{"text": "You classify on-screen text."}]},
               "contents": [{"role": "user", "parts": parts}],
               "generationConfig": {"maxOutputTokens": 10, "temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}}}
    try:
        data = _generate_content(payload, 120)
        ans = "".join(pp.get("text", "") for pp in data["candidates"][0]["content"]["parts"]).strip().lower()
        for k in ("subtitles", "lesson", "page", "none"):
            if k in ans:
                return k
    except Exception as e:
        print(f"[TEXTMODE] detection failed: {e}")
    return "none"


def _space_transcribe_text(media_path: str) -> str:
    """Whole-file transcription by the ASR Space (NeMo, Tifinagh); '' on any failure."""
    try:
        space = os.getenv("HUGGINGFACE_ASR_SPACE_URL", ASR_SPACE_DEFAULT)
        hf_token = os.getenv("HUGGINGFACE_API_KEY")
        headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
        with open(media_path, "rb") as f:
            r = requests.post(resolve_hf_space_host(space) + "/transcribe",
                              files={"audio_file": (os.path.basename(media_path), f, "application/octet-stream")},
                              headers=headers, timeout=900)
        return (r.json().get("text") or "").strip() if r.status_code == 200 else ""
    except Exception as e:
        print(f"[PAGE] narration transcription failed: {e}")
        return ""


_REPEATED_WORD = re.compile(r"^(\S+)(\s+\1){2,}$")


def read_page_text(video_path: str, tmp_dir: str, n_frames: int = 8) -> List[str]:
    """A narrated page -> «unit | Catalan meaning» lines (units of <= 10 words).
    The narration is transcribed by the ASR Space (the WORDS); Gemini then reads the page
    frame holding that transcript as a prior (the LETTERS). Measured on «La cavalleria»
    (Tamazight For All, 2026-10-19): 10 units, aligned, vs. garbage from the page alone.
    Lines are machine output and become DRAFT drills."""
    if not gemini_available():
        return []
    import base64
    from gemini_client import _generate_content
    asr_text = _space_transcribe_text(video_path)
    if not asr_text:
        print("[PAGE] no narration transcript: page reading skipped")
        return []
    try:
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video_path],
                                   capture_output=True, text=True, timeout=60).stdout.strip() or 0)
    except Exception:
        dur = 0.0
    # A story turns pages: sample frames across the whole video (never the first/last 4 %,
    # which are title cards and credits) and give them all to the model, in order.
    n = max(1, min(n_frames, int(dur // 6) if dur else n_frames))
    parts: List[Dict[str, Any]] = []
    for i in range(n):
        at = dur * (0.04 + 0.92 * (i + 0.5) / n) if dur else 1.0
        frame = os.path.join(tmp_dir, f"page_frame_{i:02d}.jpg")
        try:
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{max(0.0, at):.2f}", "-i", video_path,
                            "-frames:v", "1", "-vf", "scale=1280:-2", frame], check=True, capture_output=True, timeout=120)
            with open(frame, "rb") as fh:
                parts.append({"text": f"[frame at {at:.0f}s]"})
                parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(fh.read()).decode()}})
        except Exception as e:
            print(f"[PAGE] frame {i} failed: {e}")
    if not parts:
        return []
    prompt = ("These frames, in time order, come from ONE video in which pages of Amazigh (Tamazight) text in Tifinagh "
              "are shown while a narrator reads them; the same page appears in several frames and a story may turn "
              "pages. A speech recogniser heard the whole narration as:\n«" + asr_text[:6000] + "»\n\nUsing the pages as the "
              "authority for the LETTERS and the recognised speech as a guide to the WORDS and to the ORDER, write the "
              "whole text exactly once, in standard IRCAM Tifinagh orthography, split into short units of at most 10 "
              "words (break at sentence ends and commas), one per line, each followed by ' | ' and its Catalan meaning. "
              "Never repeat a page that was already written; do not invent words that are on neither the pages nor the "
              "recording; skip titles, logos, channel names and watermarks. Answer with the lines only.")
    payload = {"systemInstruction": {"parts": [{"text": "You read Tifinagh pages carefully and never invent text."}]},
               "contents": [{"role": "user", "parts": parts + [{"text": prompt}]}],
               "generationConfig": {"maxOutputTokens": 6000, "temperature": 0.0, "thinkingConfig": {"thinkingBudget": 0}}}
    try:
        data = _generate_content(payload, 240)
        text = "".join(pp.get("text", "") for pp in data["candidates"][0]["content"]["parts"])
    except Exception as e:
        print(f"[PAGE] page reading failed: {e}")
        return []
    lines, seen = [], set()
    for raw in text.splitlines():
        l = raw.strip().strip("-•*").strip()
        if "|" not in l:
            continue
        unit = l.split("|", 1)[0].strip()
        if not unit or unit in seen or not re.search(r"[\u2D30-\u2D7F]", unit) or _REPEATED_WORD.match(unit):
            continue
        seen.add(unit)
        lines.append(unit + " | " + l.split("|", 1)[1].strip())
    print(f"[PAGE] narration {len(asr_text)} chars + {n} page frames -> {len(lines)} units")
    return lines


def page_segments_to_drafts(segments: List[Dict]) -> List[Dict]:
    """Page units are machine output: the Tamazight goes to the suggestion field, the Catalan
    meaning stays; nothing is written as confirmed text."""
    for seg in segments:
        tz = (seg.get("text_tachelhit") or seg.get("text") or "").strip()
        if tz:
            seg["text_tachelhit_suggested"] = tz
        seg["text_tachelhit"] = None
        seg["text"] = ""
        seg["page_draft"] = True
    return segments


def read_burned_subtitles(video_path: str, tmp_dir: str, every: float = 1.0, batch: int = 10) -> List[Dict[str, Any]]:
    """Burned-in subtitles -> cues with Tachelhit (Latin) + translations + seconds."""
    if not gemini_available():
        return []
    frames = extract_frames(video_path, os.path.join(tmp_dir, "subframes"), every=every, width=800)
    items: List[Dict[str, Any]] = []
    for i in range(0, len(frames), batch):
        try:
            items.extend(_subtitle_frames_from_gemini(frames[i:i + batch]))
        except Exception as e:
            print(f"[SUBS] frame batch {i // batch} failed: {e}")
    cues = merge_subtitle_frames(items, every=every)
    print(f"[SUBS] {len(frames)} frames -> {len(items)} readings -> {len(cues)} subtitle cues")
    return cues


def looks_like_junk_asr(text: Optional[str], attested: bool = True) -> Optional[str]:
    """Return a reason string if `text` should not be stored, else None.
    `attested=False` (foreign-source draft mode) skips the English check."""
    t = (text or "").strip()
    if not t:
        return None
    if _JUNK_REPEAT_RUN.search(t):
        return "repeated-run"
    toks = re.findall(r"[^\W\d_]+", t.lower())
    if len(toks) >= 6:
        from collections import Counter
        if Counter(toks).most_common(1)[0][1] / len(toks) >= 0.4:
            return "repeated-tokens"
    if attested and not _TIFINAGH_RE.search(t):
        hits = len(_JUNK_ENGLISH.findall(t))
        words = max(1, len(re.findall(r"[A-Za-z']+", t)))
        # 3 hits, or 2 hits in a short segment ("I can't bear to fall asleep")
        if hits >= 3 or (hits >= 2 and hits / words >= 0.25):
            return "looks-english"
    return None

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs ON STARTUP
    print("[INIT] Startup lifespan events...")
    if os.getenv("LEXICON_WARMUP", "1") == "1" and not os.getenv("PYTEST_CURRENT_TEST"):
        lexicon.warm_up_async()  # dictionary + conjugation tables for the tutor (background download)

    # Optionally check and fix schema before creating tables
    # Set CHECK_SCHEMA environment variable to "1" to enable
    if os.getenv("CHECK_SCHEMA") == "1":
        print("[SCHEMA] Checking and fixing schema...")
        try:
            from check_and_fix_schema import check_and_fix
            # Run in a separate thread if it's very slow
            await asyncio.to_thread(check_and_fix)
            print("[SCHEMA] Schema check complete.")
        except Exception as e:
            print(f"[SCHEMA] ERROR during schema check: {e}")
            import traceback
            traceback.print_exc()

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Lightweight schema sync: create_all only creates NEW tables; it never
    # alters existing ones. Add any missing nullable columns so model changes
    # deploy without hand-written migrations (works on SQLite and Postgres).
    try:
        from sqlalchemy import inspect as sa_inspect, text as sa_text
        inspector = sa_inspect(engine)
        with engine.begin() as conn:
            for table in Base.metadata.sorted_tables:
                if not inspector.has_table(table.name):
                    continue
                existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
                for col in table.columns:
                    if col.name in existing_cols or col.primary_key or not col.nullable:
                        continue
                    coltype = col.type.compile(engine.dialect)
                    conn.execute(sa_text(f'ALTER TABLE {table.name} ADD COLUMN {col.name} {coltype}'))
                    print(f"[SCHEMA] Added missing column {table.name}.{col.name} ({coltype})")
    except Exception as e:
        print(f"[SCHEMA] Column sync skipped: {e}")

    # Dead-job reaper (P4.6): background jobs live in this process, so a redeploy / spin-down
    # kills them mid-flight and left the row forever in TRANSLATING (a 2-hour grace used to hide
    # it). A process that has just started cannot be running any job: every non-terminal job is
    # dead, and the capture request it came from goes back to the agent's queue.
    try:
        with SessionLocal() as db:
            n_jobs, n_req = reap_dead_jobs(db)
            if n_jobs:
                print(f"[INIT] Reaped {n_jobs} dead video job(s); {n_req} capture request(s) re-queued")
    except Exception as e:
        print(f"[INIT] Dead-job reaper skipped: {e}")

    # The course writes itself: after a deploy (or a change in the lesson's shape) every unit whose
    # lesson is missing or outdated is written here, one at a time and out of the way, so no learner
    # is the one who waits for Gemini. Set GRAMMAR_SELF_WRITE=0 to leave the lessons alone.
    if os.getenv("GRAMMAR_SELF_WRITE", "1") != "0":
        threading.Thread(target=_write_missing_lessons, daemon=True).start()

    # And it explains its own examples: for every sentence a unit can quote, why that sentence is
    # in that unit. Written here, never by a page. Set GRAMMAR_NOTES_WRITE=0 to leave them alone.
    if os.getenv("GRAMMAR_NOTES_WRITE", "1") != "0":
        threading.Thread(target=_write_missing_notes, daemon=True).start()

    # The practices made before ADR 0002 become steps, one per sentence, so they can be edited
    # like any other. Only those that have none, so this can run on every boot.
    try:
        practice_steps.convert_missing(SessionLocal)
        practice_steps.retire_spoken_steps(SessionLocal)
        practice_steps.repair_pointless_steps(SessionLocal)
    except Exception as e:
        print(f"[PRACTICE] conversion skipped: {e}")

    # Add sample data if database is empty
    with SessionLocal() as db:
        count = db.query(DrillModel).count()
        print(f"[INIT] Database has {count} drills")
        if count == 0:
            print("[INIT] Adding sample drills...")
            samples = [
                DrillModel(
                    text_catalan="Hola",
                    text_tachelhit="ⴰⵣⵓⵍ",
                    text_arabic="مرحبا",
                    tag="greeting"
                ),
                DrillModel(
                    text_catalan="Com et dius?",
                    text_tachelhit="ⵎⴰⵏⵉⵙ ⵉⵙⵎ ⵏⵏⴽ?",
                    text_arabic="ما اسمك؟",
                    tag="introduction"
                ),
                DrillModel(
                    text_catalan="Gràcies",
                    text_tachelhit="ⵜⴰⵏⵎⵎⵉⵔⵜ",
                    text_arabic="شكرا",
                    tag="courtesy"
                )
            ]
            try:
                for sample in samples:
                    db.add(sample)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"[INIT] ERROR adding sample drills: {e}")

    # Pre-check the configured translation Space. If it's a dead override (a
    # deleted/renamed Space, e.g. a stale HUGGINGFACE_TRANSLATION_SPACE_URL env
    # var), mark it dead now so NO translation call ever wastes time retrying it
    # — the built-in default Space is used from the very first request. Runs in
    # the background so it never delays startup.
    import threading as _threading

    def _probe_translation_space():
        cfg = HUGGINGFACE_TRANSLATION_SPACE_URL
        if not cfg or cfg == HF_TRANSLATION_SPACE_DEFAULT:
            return
        try:
            r = requests.get(_hf_space_url(cfg), timeout=8)
            if r.status_code in (401, 403, 404):
                _dead_translation_spaces.add(cfg)
                print(f"[INIT] Configured translation Space unreachable ({r.status_code}); using default.")
        except Exception:
            _dead_translation_spaces.add(cfg)
            print("[INIT] Configured translation Space unreachable; using default.")

    _threading.Thread(target=_probe_translation_space, daemon=True).start()

    yield
    # This runs ON SHUTDOWN
    print("[INIT] Shutdown lifespan events...")

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

app = FastAPI(title="Tamazight Drills API", lifespan=lifespan)

# ---- Error envelope (P4.10): every error body is {"detail": str, "code": str}.
# The 500 handler runs OUTSIDE CORSMiddleware (ServerErrorMiddleware is the
# outermost layer), so it has to add CORS headers itself — echoing the request
# Origin only when it is an allowed one, never "*".
_HTTP_CODES = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found",
               409: "conflict", 413: "payload_too_large", 415: "unsupported_media_type",
               422: "validation_error", 429: "rate_limited", 500: "internal_error",
               502: "bad_gateway", 503: "service_unavailable", 504: "gateway_timeout"}

def _cors_headers_for(request) -> dict:
    """CORS headers for a response built outside CORSMiddleware (see above)."""
    origin = (request.headers.get("origin") or "").strip()
    if not origin:
        return {}
    ok = origin in allowed_origins
    rx = cors_kwargs.get("allow_origin_regex")
    if not ok and rx:
        ok = re.fullmatch(rx, origin) is not None
    if not ok:
        return {}
    return {"Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin"}

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"[GLOBAL ERROR] {type(exc).__name__}: {str(exc)}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}", "code": "internal_error",
                 "type": type(exc).__name__},
        headers=_cors_headers_for(request),
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Keep FastAPI's {"detail": ...} shape for HTTPException, add "code"."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": _HTTP_CODES.get(exc.status_code, "http_error")},
        headers=exc.headers,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"[VALIDATION ERROR] {exc.errors()}")
    try:
        errors = jsonable_encoder(exc.errors())
    except Exception:
        errors = [{"loc": list(e.get("loc", ())), "msg": e.get("msg"), "type": e.get("type")}
                  for e in exc.errors()]
    parts = []
    for e in errors:
        loc = [str(p) for p in (e.get("loc") or ())]
        field = ".".join(loc[1:] if loc and loc[0] in ("body", "query", "path", "header") else loc) or "body"
        parts.append(f"{field}: {e.get('msg')}")
    return JSONResponse(
        status_code=422,
        content={"detail": "; ".join(parts) or "validation error", "code": "validation_error",
                 "errors": errors},
        headers=_cors_headers_for(request),
    )

# Development mode flag - enable automatically for SQLite (local dev)
DEVELOPMENT_MODE = DATABASE_URL.startswith("sqlite") or os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"

# Optional API-key gate for all mutating requests. When the API_KEY env var is
# set, POST/PUT/DELETE/PATCH require a matching X-API-Key header (the frontend
# sends it when VITE_API_KEY is set). When unset, the API stays open as before.
# Registered before CORSMiddleware so CORS wraps it and 401s carry CORS headers.
API_KEY = (os.getenv("API_KEY") or "").strip()
PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

@app.middleware("http")
async def never_serve_yesterday(request, call_next):
    """Cap resposta d'aquesta API es pot reaprofitar.

    Res del que torna val per a dues persones diferents ni per a dos moments diferents: les
    llistes depenen de qui pregunta i canvien així que algú escriu. Sense cap directiva, un
    navegador aplica el seu propi criteri i pot servir una resposta desada fa un instant — i
    això va passar: una petició creada correctament va aparèixer com a «res pendent aquí»,
    perquè la llista que es va tornar a demanar venia de just abans de crear-la.

    Els fitxers de debò (imatges, àudio, vídeo) no passen per aquí: són a Cloudinary.
    """
    response = await call_next(request)
    response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.middleware("http")
async def require_api_key(request, call_next):
    if API_KEY and request.method in PROTECTED_METHODS:
        provided = request.headers.get("x-api-key", "")
        if not secrets.compare_digest(provided, API_KEY):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid API key"})
    return await call_next(request)

# CORS configuration - allow frontend URL
allowed_origins_base = [
    "http://localhost:5173",
    "http://localhost:4173",
    "https://tachelhit-drills.vercel.app",
    "https://tamazight-drills.vercel.app",   # the app's name since 2026-10-21 (Tamazight Drills)
    "https://tamazigh-drills.vercel.app",
    "https://amazigh-drills.vercel.app",
    "http://localhost",              # Add this for Android APK
    "https://localhost",              # Add this for Android APK
    "capacitor://localhost",         # Add this for mobile WebView
]



# Remove duplicates and None values
# FRONTEND_URL environment variable is no longer explicitly added to this list for CORS
allowed_origins = list(set(filter(None, allowed_origins_base)))

if DEVELOPMENT_MODE:
    print("[CORS] DEVELOPMENT MODE ENABLED - adding extra localhost origins")
    allowed_origins.append("http://localhost:8000")
    allowed_origins.append("http://127.0.0.1:5173")
    allowed_origins = list(set(allowed_origins))

print("=" * 80)
print("CORS CONFIGURATION")
print("=" * 80)
print(f"FRONTEND_URL from env: {FRONTEND_URL}")
print(f"DEVELOPMENT_MODE: {DEVELOPMENT_MODE}")
print(f"Allowed origins: {allowed_origins}")
print("=" * 80)

cors_kwargs = dict(
    allow_origins=allowed_origins,
    allow_origin_regex=r"https://(tachelhit|tamazight|tamazigh|amazigh)-drills(-[a-z0-9-]+)?[.]vercel[.]app",  # the project's own domains and preview deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)
if DEVELOPMENT_MODE:
    # Allow dev-server pages served over the LAN (e.g. phone testing against
    # `npm run dev --host`); private-range IPs only, dev mode only.
    cors_kwargs["allow_origin_regex"] = (
        r"http://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?"
    )
app.add_middleware(CORSMiddleware, **cors_kwargs)

# JSON answers go out uncompressed otherwise -- the drills list alone was 5.7 MB over the wire
# on every load (issue #190). Text like this shrinks about eight times. Anything under a kilobyte
# is left alone: compressing it would cost more than it saves.
app.add_middleware(GZipMiddleware, minimum_size=1024)

import mimetypes

# Ensure .webm is recognized as audio/webm
mimetypes.add_type("audio/webm", ".webm")
app.mount("/media", StaticFiles(directory=MEDIA_ROOT), name="media")

# Debug endpoint
@app.get("/")
def root():
    return {
        "status": "online",
        "frontend_url": FRONTEND_URL,
        "allowed_origins": allowed_origins,
        "endpoints": [
            "/drills/",
            "/tests/",
            "/test-attempts/",
            "/shorts/"
        ]
    }

@app.get("/debug/routes")
def list_routes():
    routes_info = []
    for route in app.routes:
        info = {"path": getattr(route, "path", str(route)), "name": getattr(route, "name", "unnamed")}
        if hasattr(route, "methods"):
            info["methods"] = list(route.methods)
        routes_info.append(info)
    return routes_info

@app.get("/health")
def health_check():
    print(f"[HEALTH] Health check requested at {datetime.utcnow().isoformat()}")
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "frontend_url": FRONTEND_URL,
        "api_base": "https://tachelhit-drills-api.onrender.com",
        "cors_allowed": allowed_origins,
        "service": "tachelhit-drills-backend",
        "mobile_support": True,
        "mobile_friendly": True,
        "features": {
            "video_generation": True,
            "image_generation": True,
            "audio_trimming": True,
            "transcription": True,
            "translation": True,
            "demo_videos": True,
            "youtube_shorts": True,
            "responsive_ui": True
        }
    }

@app.get("/mobile-config")
def mobile_config():
    """
    Provide configuration details useful for mobile frontend.
    """
    return {
        "cloudinary_configured": bool(os.getenv("CLOUDINARY_CLOUD_NAME")),
        "huggingface_space_url": os.getenv("HUGGINGFACE_SPACE_URL"),
        "huggingface_asr_space_url": os.getenv("HUGGINGFACE_ASR_SPACE_URL"),
        "huggingface_translation_space_url": HUGGINGFACE_TRANSLATION_SPACE_URL,
        "max_upload_size_mb": 100,
        "supported_media_formats": {
            "audio": ["webm", "mp4", "ogg", "wav", "m4a", "mp3", "aac"],
            "video": ["mp4", "webm", "mov", "avi", "m4v"],
            "image": ["jpg", "jpeg", "png", "gif", "webp"]
        },
        "endpoints": {
            "drills": "/drills/",
            "tests": "/tests/",
            "upload_media": "/upload-media/{drill_id}/{media_type}",
            "generate_image": "/generate-image/{drill_id}",
            "generate_short": "/generate-short/{drill_id}",
            "generate_demo": "/generate-drillplayer-demo/{test_id}",
            "transcribe": "/transcribe/",
            "translate": "/translate/",
            "video_analysis": "/video-analysis/upload"
        },
        "ui_features": {
            "drill_card": True,
            "drill_editor": True,
            "image_generation": True,
            "audio_recording": True,
            "video_playback": True,
            "transcription_interface": True,
            "test_taking": True,
            "responsive_layout": True,
            "touch_friendly_buttons": True
        },
        "mobile_optimized": True
    }

@app.get("/test-connection")
def test_connection():
    """Simple endpoint to test frontend-backend connection"""
    return {
        "message": "Backend is reachable",
        "timestamp": datetime.utcnow().isoformat(),
        "frontend_url": FRONTEND_URL,
        "cors_origin": "https://tachelhit-drills.vercel.app"
    }

@app.post("/translate")
@app.post("/translate/")
async def translate_text_endpoint(request: TranslateRequest):
    """
    Translate text between supported languages (Catalan, Tachelhit, Arabic, etc.)
    """
    print(f"[TRANSLATE ENDPOINT] Received request: text='{request.text}', source_lang='{request.source_lang}', target_lang='{request.target_lang}'")
    src_code = LANGUAGE_CODE_MAP.get(request.source_lang, request.source_lang)
    tgt_code = LANGUAGE_CODE_MAP.get(request.target_lang, request.target_lang)
    print(f"[TRANSLATE ENDPOINT] Mapped codes: src_code='{src_code}', tgt_code='{tgt_code}'")
    try:
        translation = await asyncio.to_thread(translate_with_hf, request.text, src_code, tgt_code)
        print(f"[TRANSLATE ENDPOINT] Result translation: '{translation}'")
        return TranslateResponse(translated_text=translation)
    except Exception as e:
        print(f"[TRANSLATE ENDPOINT ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _hash_token(raw: str) -> str:
    """Tokens are stored hashed; only the user ever holds the raw value."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[UserModel]:
    """Resolve the requesting user from the X-User-Token header.

    No header -> None (anonymous, as before). A header that matches no user
    -> 401 (P4.4): a stale/rotated token must not silently degrade a learner
    to the shared anonymous schedule. The frontend only sends the header when
    it holds a token, so anonymous flows are unaffected."""
    token = (request.headers.get("x-user-token") or "").strip()
    if not token:
        return None
    h = _hash_token(token)
    user = db.query(UserModel).filter(UserModel.token == h).first()
    if user is None:
        sess = db.query(UserSessionModel).filter(UserSessionModel.token_hash == h).first()
        if sess is not None:
            user = db.query(UserModel).filter(UserModel.id == sess.user_id).first()
            if user is not None:
                sess.last_used = datetime.utcnow()
                db.commit()
    if user is None:
        raise HTTPException(status_code=401, detail="invalid token")
    return user


def require_user(user: Optional[UserModel] = Depends(get_current_user)) -> UserModel:
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Per afegir coses a la biblioteca cal un nom: fes-te'n un al teu perfil (és gratis i "
                   "triga un moment).")
    return user


def may_change(drill, user: Optional[UserModel]) -> bool:
    """A drill is whoever made it's, or an admin's. One nobody claims — almost all of the library,
    made before accounts existed — is an admin's."""
    if user is None:
        return False
    if user.is_admin:
        return True
    return bool(drill.created_by_user_id) and drill.created_by_user_id == user.id


def owner_or_admin(drill, user: Optional[UserModel], what: str = "frase") -> None:
    """Raise unless this person may change this thing, saying which of the two it is.

    `what` is the word for it, because the same rule guards sentences and practices and the
    screens now show the server's own sentence: telling somebody their PRACTICE «és una frase de
    la biblioteca» is us talking about something they cannot see."""
    if may_change(drill, user):
        return
    if user is None:
        raise HTTPException(status_code=401, detail="Entra-hi per canviar res")
    if what == "pràctica":
        if not drill.created_by_user_id:
            raise HTTPException(status_code=403, detail="Aquesta pràctica no és de ningú: demana-ho a qui administra la biblioteca")
        raise HTTPException(status_code=403, detail="Aquesta pràctica és d'algú altre: fes-te'n una de teva")
    if not drill.created_by_user_id:
        raise HTTPException(status_code=403, detail="Aquesta frase és de la biblioteca: demana-ho a qui l'administra, o desa la teva versió")
    raise HTTPException(status_code=403, detail="Aquesta frase és d'algú altre: desa la teva versió")


def require_admin(user: UserModel = Depends(require_user)) -> UserModel:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


# ---- Accounts: e-mail + password on top of the token identity -------------------------
_PW_ITERS = 200_000
_login_attempts: Dict[str, List[float]] = {}


def _hash_password(pw: str) -> str:
    import hashlib
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt.encode("utf-8"), _PW_ITERS)
    return f"pbkdf2_sha256${_PW_ITERS}${salt}${dk.hex()}"


def _verify_password(pw: str, stored: Optional[str]) -> bool:
    import hashlib, hmac
    try:
        algo, iters, salt, digest = (stored or "").split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt.encode("utf-8"), int(iters))
        return hmac.compare_digest(dk.hex(), digest)
    except (ValueError, AttributeError):
        return False


def _admin_emails() -> set:
    return {e.strip().lower() for e in (os.getenv("ADMIN_EMAILS") or "").split(",") if e.strip()}


def _no_admin_yet(db) -> bool:
    """True while nobody can administer this library. The first account then becomes the
    administrator, so a fresh database (or one whose only admin was a token identity that is gone)
    is not left with no way in; once an admin exists this never fires again."""
    return db.query(UserModel).filter(UserModel.is_admin.is_(True)).count() == 0


def _valid_email(e: str) -> bool:
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e or ""))


def _check_password_strength(pw: str) -> None:
    if len(pw or "") < 8:
        raise HTTPException(status_code=400, detail="La contrasenya ha de tenir almenys 8 caràcters")


def _new_session(db: Session, user: UserModel, device: Optional[str]) -> str:
    raw = secrets.token_hex(24)
    db.add(UserSessionModel(user_id=user.id, token_hash=_hash_token(raw), device=(device or "")[:120] or None))
    db.commit()
    return raw


def _rate_limit(bucket: Dict[str, List[float]], key: str, limit: int, window: int) -> None:
    now_ts = datetime.utcnow().timestamp()
    attempts = [t for t in bucket.get(key, []) if now_ts - t < window]
    if len(attempts) >= limit:
        raise HTTPException(status_code=429, detail="Massa intents; torna-ho a provar més tard")
    attempts.append(now_ts)
    bucket[key] = attempts


def _user_payload(user: UserModel) -> dict:
    return {"username": user.username, "display_name": user.display_name, "email": user.email,
            "variety": user.variety, "region": user.region, "is_admin": bool(user.is_admin),
            "is_native": user.is_native, "has_password": bool(user.password_hash)}


MAIL_KEYS = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS", "SMTP_FROM", "MAIL_API_PROVIDER", "MAIL_API_KEY")


def _mail_ready() -> bool:
    """Can this server send mail at all: an HTTPS provider, or a full SMTP sender."""
    api = mail_setting("MAIL_API_PROVIDER") and mail_setting("MAIL_API_KEY") and (mail_setting("SMTP_FROM") or mail_setting("SMTP_USER"))
    smtp = mail_setting("SMTP_HOST") and mail_setting("SMTP_USER") and mail_setting("SMTP_PASS")
    return bool(api or smtp)


def mail_setting(key: str) -> str:
    """A mail setting: what an admin saved in the app, else the server environment."""
    try:
        with SessionLocal() as db:
            row = db.query(AppSettingModel).filter(AppSettingModel.key == key).first()
            if row and (row.value or "").strip():
                return row.value.strip()
    except Exception as e:
        print(f"[MAIL] settings unavailable: {e}")
    return (os.getenv(key) or "").strip()


def _send_email_api(to: str, subject: str, body: str) -> bool:
    """Send over HTTPS through a mail provider (Resend or Brevo). Hosts that block the SMTP ports
    (Render does) can still send this way. Returns False when no provider is configured."""
    provider = mail_setting("MAIL_API_PROVIDER").lower()
    key = mail_setting("MAIL_API_KEY")
    sender = mail_setting("SMTP_FROM") or mail_setting("SMTP_USER")
    if not provider or not key or not sender:
        return False
    if provider == "resend":
        r = requests.post("https://api.resend.com/emails", headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                          json={"from": sender, "to": [to], "subject": subject, "text": body}, timeout=30)
    elif provider == "brevo":
        r = requests.post("https://api.brevo.com/v3/smtp/email", headers={"api-key": key, "Content-Type": "application/json"},
                          json={"sender": {"email": sender}, "to": [{"email": to}], "subject": subject, "textContent": body}, timeout=30)
    else:
        raise RuntimeError(f"Unknown mail provider: {provider}")
    if r.status_code >= 300:
        raise RuntimeError(f"{provider} {r.status_code}: {r.text[:200]}")
    return True


def _smtp_connect(host: str, port: int, timeout: int = 30):
    """Open an SMTP connection, IPv4 first (a host with no IPv6 route answers «Network is
    unreachable» when the name resolves to IPv6), trying STARTTLS on the given port and implicit
    TLS on 465. Raises the last error when nothing connects."""
    import smtplib, socket, ssl
    last = None
    for p, implicit in ((port, False), (465, True)) if port != 465 else ((465, True), (587, False)):
        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                infos = socket.getaddrinfo(host, p, family, socket.SOCK_STREAM)
            except OSError as e:
                last = e; continue
            for *_ , addr in [i[:5] for i in infos][:3]:
                try:
                    sock = socket.create_connection(addr[:2], timeout)
                    if implicit:
                        smtp = smtplib.SMTP_SSL(timeout=timeout, context=ssl.create_default_context())
                        smtp.sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
                        smtp.file = smtp.sock.makefile("rb"); smtp._host = host
                        smtp.getreply(); smtp.ehlo()
                    else:
                        smtp = smtplib.SMTP(timeout=timeout)
                        smtp.sock = sock; smtp.file = sock.makefile("rb"); smtp._host = host
                        smtp.getreply(); smtp.ehlo(); smtp.starttls(context=ssl.create_default_context()); smtp.ehlo()
                    return smtp
                except Exception as e:
                    last = e
                    try: sock.close()
                    except Exception: pass
    raise last or RuntimeError("no route to the mail server")


def _send_email(to: str, subject: str, body: str) -> bool:
    """Send a message. An HTTPS provider is used when one is configured (the only way out of hosts
    that block SMTP); otherwise SMTP from the saved settings, else the environment. False when
    nothing is configured."""
    if _send_email_api(to, subject, body):
        return True
    host, user_, pw = mail_setting("SMTP_HOST"), mail_setting("SMTP_USER"), mail_setting("SMTP_PASS")
    if not (host and user_ and pw):
        return False
    from email.message import EmailMessage
    msg = EmailMessage()
    msg["From"] = mail_setting("SMTP_FROM") or user_
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    smtp = _smtp_connect(host, int(mail_setting("SMTP_PORT") or 587))
    try:
        smtp.login(user_, pw)
        smtp.send_message(msg)
    finally:
        try: smtp.quit()
        except Exception: pass
    return True


def reap_dead_jobs(db) -> tuple:
    """Mark every non-terminal video job FAILED («died with the server») and put the capture
    request that was waiting on it back to `pending`, so the local agent uploads it again.
    Called at startup, when no job can legitimately be running in this process."""
    dead = db.query(VideoProcessingJobModel).filter(~VideoProcessingJobModel.status.in_(JOB_TERMINAL_STATUSES)).all()
    requeued = 0
    for j in dead:
        j.status = "FAILED"
        j.error_message = "died with the server (restart or deploy); the capture request was re-queued"
        for req in db.query(CaptureRequestModel).filter(CaptureRequestModel.job_id == j.id,
                                                        CaptureRequestModel.status.notin_(("done", "failed"))).all():
            req.status = "pending"; req.claimed_at = None; req.job_id = None; req.error = "re-queued: the server restarted mid-job"
            requeued += 1
    if dead:
        db.commit()
    return len(dead), requeued
DEFAULT_TZ = "Europe/Madrid"

# ---- Pagination + delta-sync helpers (P4.1-4.3)
DEFAULT_PAGE_LIMIT = 100
MAX_PAGE_LIMIT = 500
JOB_TERMINAL_STATUSES = ("COMPLETED", "FAILED")


def _page_bounds(limit: Optional[int], offset: Optional[int]):
    """None = no pagination (legacy "return everything"); else (offset, limit)."""
    if limit is None and offset is None:
        return None
    lim = DEFAULT_PAGE_LIMIT if limit is None else limit
    return max(0, offset or 0), max(1, min(lim, MAX_PAGE_LIMIT))

def _paginate(query, response: Response, limit: Optional[int], offset: Optional[int]):
    """Apply limit/offset to a query and set X-Total-Count (count BEFORE paging).

    Backwards compatibility: when neither limit nor offset is given, every row
    is returned (the current web frontend loads all ~600 drills in one call).
    When either is given, limit defaults to 100 and is capped at 500."""
    response.headers["X-Total-Count"] = str(query.order_by(None).count())
    bounds = _page_bounds(limit, offset)
    if bounds is None:
        return query.all()
    off, lim = bounds
    return query.offset(off).limit(lim).all()

def _parse_since(since: str) -> datetime:
    """ISO-8601 -> naive UTC datetime (what the DB stores). 400 on garbage."""
    try:
        dt = datetime.fromisoformat(since.strip())
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="since must be an ISO-8601 timestamp")
    return _to_naive_utc(dt)

def _to_naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt

def _parse_ids(ids: str) -> list[int]:
    out: list[int] = []
    for part in ids.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            n = int(part)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"ids must be comma-separated integers (got {part!r})")
        if n not in out:
            out.append(n)
    return out

def _user_zone(user: Optional[UserModel]):
    """The learner's IANA zone (P4.10); unknown/missing -> Europe/Madrid, and
    if even that cannot load (no tz database) -> UTC."""
    name = (getattr(user, "tz", None) if user else None) or DEFAULT_TZ
    for candidate in (name, DEFAULT_TZ):
        try:
            return ZoneInfo(candidate)
        except Exception:
            continue
    return timezone.utc

def _local_day(naive_utc: datetime, zone):
    return naive_utc.replace(tzinfo=timezone.utc).astimezone(zone).date()

class TtsRequest(BaseModel):
    text: str
    drill_id: Optional[int] = 0
    meaning: Optional[str] = None  # Catalan meaning: lets the spelling be normalised for the voice

def _needs_tts(drill) -> bool:
    """A confirmed text without a current (v2) synthetic voice."""
    t = (drill.text_tachelhit or "").strip()
    return bool(t) and t.lower() != "text" and f"tts_{VOICE_VERSION}_" not in (drill.audio_tts_shi_url or "")


def prefill_tts(drill, db) -> Optional[str]:
    """Make and store the synthetic voice of a drill whose text is confirmed. Best effort:
    returns the url or None; never raises (the drill is fine without a voice)."""
    try:
        if not _needs_tts(drill):
            return drill.audio_tts_shi_url
        spoken, _how = tts_text(drill.text_tachelhit, drill.text_catalan)
        if not spoken:
            return None
        url = generate_tachelhit_tts_hf(spoken, drill.id)
        drill.audio_tts_shi_url = url
        db.commit()
        return url
    except Exception as e:
        print(f"[TTS-PREFILL] drill {getattr(drill, 'id', '?')}: {e}")
        return None


@app.post("/tts/prefill")
async def tts_prefill(limit: int = Body(25, embed=True), tag: Optional[str] = Body(None, embed=True),
                      db: Session = Depends(get_db), _admin: UserModel = Depends(require_admin)):
    """Admin: produce the synthetic voice of up to `limit` drills with confirmed text that
    still lack one (oldest first; `tag` narrows). Call repeatedly until `remaining` is 0."""
    q = db.query(DrillModel).filter(DrillModel.text_tachelhit != None, DrillModel.text_tachelhit != "")
    if tag:
        q = q.filter(DrillModel.tag.ilike(f"%{tag}%"))
    todo = [d for d in q.order_by(DrillModel.id.asc()).all() if _needs_tts(d)]
    done, failed = [], []
    for d in todo[:max(1, min(limit, 100))]:
        url = await asyncio.to_thread(prefill_tts, d, db)
        (done if url else failed).append(d.id)
    return {"made": done, "failed": failed, "remaining": max(0, len(todo) - len(done) - len(failed))}


@app.post("/tts/tachelhit")
@app.post("/tts/tachelhit/")
async def tachelhit_tts_endpoint(request: TtsRequest, db: Session = Depends(get_db)):
    """
    Generate Tachelhit TTS for given Tifinagh text. When a drill_id is given,
    the synthesized voice is stored on the drill (audio_tts_shi_url) so the
    player can voice text-only cards without re-synthesizing — synthetic
    audio is scaffolding for cards that lack a native recording.
    """
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Text is required")
    try:
        drill = db.query(DrillModel).filter(DrillModel.id == request.drill_id).first() if request.drill_id else None
        same = drill is not None and (drill.text_tachelhit or "").strip() == request.text.strip()
        stored = (drill.audio_tts_shi_url or "") if drill else ""
        if same and f"tts_{VOICE_VERSION}_" in stored:
            return {"url": stored, "cached": True}  # voices made before v2 were read from Latin: remade
        meaning = request.meaning or (drill.text_catalan if drill else None)
        spoken, how = await asyncio.to_thread(tts_text, request.text, meaning)
        if not spoken:
            raise HTTPException(status_code=400, detail="Nothing to read")
        url = await asyncio.to_thread(generate_tachelhit_tts_hf, spoken, request.drill_id or 0)
        if drill is not None:
            drill.audio_tts_shi_url = url
            db.commit()
        return {"url": url, "spoken_text": spoken, "how": how}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CatalanTtsRequest(BaseModel):
    drill_id: int
    force: bool = False


@app.post("/tts/catalan")
def catalan_tts_endpoint(request: CatalanTtsRequest, db: Session = Depends(get_db)):
    """Make and store the Catalan synthetic voice (audio_tts_url) of a drill that lacks one, so the
    player can say the meaning before the Tachelhit. Drills created by hand with a recording (our own
    speakers') never got one. Idempotent: an existing voice is kept unless `force`."""
    drill = db.query(DrillModel).filter(DrillModel.id == request.drill_id).first()
    if drill is None:
        raise HTTPException(status_code=404, detail="Drill not found")
    text = (drill.text_catalan or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="The drill has no Catalan text")
    if drill.audio_tts_url and not request.force:
        return {"url": drill.audio_tts_url, "cached": True}
    try:
        url = generate_catalan_tts(text, drill.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    drill.audio_tts_url = url
    db.commit()
    return {"url": url, "cached": False}


class ImportLinkRequest(BaseModel):
    url: str
    drill_id: int

@app.post("/import-link")
@app.post("/import-link/")
async def import_link_endpoint(request: ImportLinkRequest):
    """
    Download video from URL and attach to drill.
    """
    from video_utils import download_video_from_url
    try:
        url = await asyncio.to_thread(download_video_from_url, request.url, request.drill_id)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===================== CRUD =====================
@app.get("/drills/tombstones")
def get_drill_tombstones(since: Optional[str] = None, db: Session = Depends(get_db)):
    """Ids of deleted drills (P4.3), newest first; `since` (ISO-8601) narrows to
    deletions at/after that instant so a client can finish a delta sync."""
    q = db.query(DrillTombstoneModel)
    if since:
        q = q.filter(DrillTombstoneModel.deleted_at >= _parse_since(since))
    rows = q.order_by(DrillTombstoneModel.deleted_at.desc()).limit(MAX_PAGE_LIMIT * 4).all()
    return [{"drill_id": t.drill_id, "deleted_at": iso_z(t.deleted_at)} for t in rows]

# exclude_none: a drill has 40 fields and most rows leave most of them empty. Writing
# `"field":null` 3.400 times was 43% of the whole answer (issue #190). A missing key and a
# null key mean the same thing to every reader we have.
@app.get("/drills/", response_model=list[Drill], response_model_exclude_none=True)
def get_drills(response: Response, tag: Optional[str] = None, author: Optional[str] = None,
               ids: Optional[str] = None, since: Optional[str] = None, search: Optional[str] = None,
               limit: Optional[int] = None, offset: Optional[int] = None,
               db: Session = Depends(get_db)):
    """List drills, newest first.

    - `ids=1,2,3` returns only those drills, in the given order (P4.1).
    - `since=<ISO-8601>` returns drills changed (or created) at/after that
      instant; pair with GET /drills/tombstones?since= for deletions (P4.3).
    - `limit`/`offset` paginate (P4.2): limit defaults to 100 and is capped at
      500 **only when at least one of them is sent**. With neither, ALL rows
      are returned, as the current frontend expects. `X-Total-Count` always
      carries the unpaginated count.
    """
    try:
        query = db.query(DrillModel)

        if tag:
            # Simple substring match for tags (since they can be comma-separated)
            query = query.filter(DrillModel.tag.ilike(f"%{tag}%"))

        if author:
            query = query.filter(DrillModel.author.ilike(f"%{author}%"))

        if search and search.strip():
            # Finding a sentence to put in a practice must not mean downloading the library:
            # the search happens here, over both texts and the tag (issue #199).
            from sqlalchemy import or_ as _or_search
            needle = f"%{search.strip()}%"
            query = query.filter(_or_search(DrillModel.text_catalan.ilike(needle),
                                            DrillModel.text_tachelhit.ilike(needle),
                                            DrillModel.tag.ilike(needle)))

        if since:
            query = query.filter(
                sa_func.coalesce(DrillModel.updated_at, DrillModel.date_created) >= _parse_since(since)
            )

        if ids is not None:
            wanted = _parse_ids(ids)
            rows = query.filter(DrillModel.id.in_(wanted)).all() if wanted else []
            by_id = {d.id: d for d in rows}
            drills = [by_id[i] for i in wanted if i in by_id]
            response.headers["X-Total-Count"] = str(len(drills))
            bounds = _page_bounds(limit, offset)
            if bounds is not None:
                off, lim = bounds
                drills = drills[off:off + lim]
        else:
            drills = _paginate(query.order_by(DrillModel.date_created.desc()), response, limit, offset)
        print(f"[API] GET /drills/ (tag={tag}, author={author}, ids={ids}, since={since}, "
              f"limit={limit}, offset={offset}) returning {len(drills)} drills")
        # Intentar serializar cada drill para detectar errores de validación Pydantic
        serialized_drills = []
        for drill in drills:
            try:
                # Usar el modelo Pydantic Drill para validar
                drill_schema = Drill.from_orm(drill)
                serialized_drills.append(drill_schema)
            except Exception as e:
                print(f"[API] WARNING: Drill {drill.id} failed validation: {e}")
                # Si falla, intentar normalizar las URLs manualmente antes de serializar
                # Crear un diccionario con los campos, aplicando normalize_media_url a las URLs
                drill_dict = {
                    'id': drill.id,
                    'date_created': drill.date_created,
                    'tag': drill.tag,
                    'text_catalan': drill.text_catalan,
                    'text_tachelhit': drill.text_tachelhit,
                    'text_arabic': drill.text_arabic,
                    'audio_url': normalize_media_url(drill.audio_url) if drill.audio_url else None,
                    'audio_tts_url': normalize_media_url(drill.audio_tts_url) if drill.audio_tts_url else None,
                    'video_url': normalize_media_url(drill.video_url) if drill.video_url else None,
                    'image_url': normalize_media_url(drill.image_url) if drill.image_url else None,
                }
                # Crear el objeto Pydantic con el diccionario corregido
                drill_schema = Drill(**drill_dict)
                serialized_drills.append(drill_schema)
        return serialized_drills
    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] ERROR in GET /drills/: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/drills/similar")
def similar_drills(text: str, field: str = "tachelhit", exclude_id: Optional[int] = None,
                   limit: int = 5, db: Session = Depends(get_db)):
    """Sentences the library may already hold that say this.

    Declared before `/drills/{drill_id}` on purpose: that route would otherwise swallow the word
    «similar» and try to read it as a number.

    Matched by SOUND, not by spelling (`practice.sound_key`, the same key the practice screen
    compares with), so «aghrum», «aɣrum» and «ⴰⵖⵔⵓⵎ» land together -- which a text search never
    would. Nothing is forbidden by this: saying the same sentence another way is what the variants
    are for. It is here so the person can choose before writing a second copy of what we have.
    """
    said = (text or "").strip()
    if len(said) < 3:
        return {"query": said, "field": field, "matches": []}
    col = DrillModel.text_catalan if field == "catalan" else DrillModel.text_tachelhit

    def key(t: str) -> str:
        return " ".join(practice_mod.sound_key(w) for w in practice_mod.words_of(t or ""))

    want = key(said)
    if not want:
        return {"query": said, "field": field, "matches": []}
    # Two columns of every sentence, not whole rows: the comparison is by sound, so no SQL filter
    # can narrow it first -- a LIKE on «aghrum» never reaches «aɣrum». Reading (id, text) for the
    # library is a few hundred kilobytes; reading the rows themselves would not be.
    q = db.query(DrillModel.id, col).filter(col != None, col != "")        # noqa: E711
    if exclude_id:
        q = q.filter(DrillModel.id != exclude_id)
    hits = [i for i, other in q.order_by(DrillModel.id.desc()).all() if key(other) == want]
    hits = hits[:max(1, min(limit, 20))]
    if not hits:
        return {"query": said, "field": field, "matches": []}
    rows = {d.id: d for d in db.query(DrillModel).filter(DrillModel.id.in_(hits)).all()}
    return {"query": said, "field": field, "matches": [
        {"id": d.id, "text_tachelhit": d.text_tachelhit, "text_catalan": d.text_catalan,
         "author": d.author, "variety": d.variety,
         "has_voice": bool(d.audio_url), "image_url": d.image_url}
        for d in (rows[i] for i in hits if i in rows)]}


@app.get("/drills/{drill_id}", response_model=Drill)
def get_drill(drill_id: int, db: Session = Depends(get_db)):
    """One drill by id (P4.1); 404 when it does not exist."""
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
    return drill

def _set_drill_key(db_drill) -> None:
    """Recompute the script-independent phonemic key from the Latin (preferred)
    or Tifinagh form, so search/dedup match across spellings and scripts."""
    from transliteration import phonemic_key
    src = (getattr(db_drill, "text_tachelhit_latin", "") or "").strip() \
        or (getattr(db_drill, "text_tachelhit", "") or "").strip()
    db_drill.text_key = phonemic_key(src) if src else None


@app.post("/drills/", response_model=Drill)
def create_drill(drill: DrillCreate = None, db: Session = Depends(get_db),
                 user: UserModel = Depends(require_user)):
    # A drill needs at least one text or one media URL; a fully empty body
    # used to create blank rows (P1.9). Checked before the try/except below,
    # which turns any exception into a 500.
    drill_data = drill.model_dump(exclude_unset=True) if drill is not None else {}
    _content_keys = ("text_catalan", "text_tachelhit", "text_arabic", "text_tachelhit_latin",
                     "audio_url", "video_url", "image_url")
    if not any(str(drill_data.get(k) or "").strip() for k in _content_keys):
        raise HTTPException(status_code=422, detail="Cal almenys un text (català, tachelhit o àrab) o un fitxer.")
    try:
        db_drill = DrillModel(**drill_data)

        # Contributor attribution + variety provenance
        if user:
            db_drill.created_by_user_id = user.id
            if not db_drill.author:
                db_drill.author = user.display_name or user.username
            # default the drill's variety/region from the contributor's declared
            # origin, so we know which variety this form was collected in
            if not db_drill.variety and user.variety:
                db_drill.variety = user.variety
            if not db_drill.region and getattr(user, "region", None):
                db_drill.region = user.region

        db.add(db_drill)
        db.commit()
        db.refresh(db_drill)

        # If Catalan text is provided, generate Arabic translation and TTS
        if db_drill.text_catalan:
            try:
                # Update Arabic translation
                db_drill.text_arabic = translator_ca_to_ar.translate(db_drill.text_catalan)
            except Exception as e:
                print("Translation error during drill creation:", e)

            # Generate TTS audio for Catalan text
            try:
                tts_url = generate_catalan_tts(db_drill.text_catalan, db_drill.id)
                db_drill.audio_tts_url = tts_url
                print(f"[TTS] Generated TTS audio for new drill {db_drill.id}: {tts_url}")
            except Exception as e:
                print(f"[TTS] Failed to generate TTS for new drill: {e}")

        _set_drill_key(db_drill)
        db.commit()
        db.refresh(db_drill)
        return db_drill
    except Exception as e:
        db.rollback()
        print(f"Error creating drill: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create drill: {e}")

@app.put("/drills/{drill_id}", response_model=Drill)
def update_drill(drill_id: int, update_data: DrillUpdate, db: Session = Depends(get_db),
                 user: Optional[UserModel] = Depends(get_current_user)):
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
    owner_or_admin(drill, user)

    update_dict = update_data.model_dump(exclude_unset=True)

    # Subjects set by hand win over the automatic catalogue and are never re-classified
    if "topics" in update_dict and "topics_source" not in update_dict:
        cleaned = topics_catalog.parse(update_dict["topics"])
        update_dict["topics"] = ", ".join(cleaned) if cleaned else None
        update_dict["topics_source"] = "owner"

    # Handle tag updates: if tag is provided, process according to prefix
    if "tag" in update_dict and update_dict["tag"] is not None:
        new_tag = update_dict["tag"].strip()
        if new_tag:
            # If the new tag starts with '+', append to existing tags
            if new_tag.startswith('+'):
                tag_to_add = new_tag[1:].strip()
                if tag_to_add:
                    current_tags = drill.tag.split(',') if drill.tag else []
                    current_tags = [t.strip() for t in current_tags if t.strip()]
                    # Remove duplicates and empty strings
                    current_tags = list(dict.fromkeys([t for t in current_tags if t]))
                    if tag_to_add not in current_tags:
                        current_tags.append(tag_to_add)
                    update_dict["tag"] = ', '.join(current_tags) if current_tags else None
            # If the new tag starts with '-', remove from existing tags
            elif new_tag.startswith('-'):
                tag_to_remove = new_tag[1:].strip()
                if tag_to_remove:
                    current_tags = drill.tag.split(',') if drill.tag else []
                    current_tags = [t.strip() for t in current_tags if t.strip()]
                    current_tags = [t for t in current_tags if t and t != tag_to_remove]
                    update_dict["tag"] = ', '.join(current_tags) if current_tags else None
            # Otherwise, replace the tag completely (but keep if empty string means clear)
            else:
                # If new_tag is empty string, set to None to clear
                if new_tag == '':
                    update_dict["tag"] = None
                # Otherwise, use the new tag as is
                else:
                    # Ensure no leading/trailing commas
                    update_dict["tag"] = new_tag.strip(', ')
        else:
            # If new_tag is empty after stripping, clear the tag
            update_dict["tag"] = None

    # Check if text_catalan is being updated and is not empty
    text_catalan_updated = "text_catalan" in update_dict and update_dict["text_catalan"]
    previous_text_catalan = drill.text_catalan

    for key, value in update_dict.items():
        setattr(drill, key, value)

    if text_catalan_updated:
        try:
            # Update Arabic translation
            drill.text_arabic = translator_ca_to_ar.translate(update_dict["text_catalan"])
        except Exception as e:
            print("Translation error:", e)

        # Generate TTS audio for Catalan text
        try:
            tts_url = generate_catalan_tts(update_dict["text_catalan"], drill_id)
            drill.audio_tts_url = tts_url
            print(f"[TTS] Generated TTS audio for drill {drill_id}: {tts_url}")
        except Exception as e:
            print(f"[TTS] Failed to generate TTS: {e}")
            # Don't raise exception to avoid breaking the update

    _set_drill_key(drill)
    drill.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(drill)
    return drill

@app.delete("/drills/{drill_id}")
def delete_drill(drill_id: int, db: Session = Depends(get_db),
                 user: Optional[UserModel] = Depends(get_current_user)):
    """Delete a drill and everything keyed on it (P4.7): review state, review
    log and extra recordings go first (explicitly — SQLite ignores FK cascades
    unless PRAGMA foreign_keys is on, and the Postgres FKs were created before
    ondelete=CASCADE existed), then a tombstone is written for delta sync."""
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
    owner_or_admin(drill, user)
    for model in (DrillReviewModel, ReviewLogModel, RecordingModel):
        db.query(model).filter(model.drill_id == drill_id).delete(synchronize_session=False)
    db.add(DrillTombstoneModel(drill_id=drill_id, deleted_at=datetime.utcnow()))
    db.delete(drill)
    db.commit()
    return {"detail": "Deleted"}

# ===================== AI Image Generation Helper =====================
HF_INFERENCE_API_URL = "https://router.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINGFACE_API_KEY")

async def generate_image_with_ai(prompt: str) -> bytes:
    """
    Generates an image using a Hugging Face Space via gradio_client.
    Returns the raw image bytes.
    """
    try:
        # Translate prompt to English
        try:
            translated_prompt = GoogleTranslator(source='ca', target='en').translate(prompt)
            print(f"[AI_IMAGE] Translated prompt: '{prompt}' -> '{translated_prompt}'")
            final_prompt = translated_prompt
        except Exception as e:
            print(f"[AI_IMAGE] Translation failed for prompt '{prompt}': {e}. Using original Catalan prompt.")
            final_prompt = prompt

        # Connect to Hugging Face Space for image generation
        space_url = HUGGINGFACE_IMAGE_SPACE_URL
        if not space_url:
            raise HTTPException(
                status_code=500,
                detail="HUGGINGFACE_IMAGE_SPACE_URL environment variable not set."
            )
        print(f"[AI_IMAGE] Connecting to Hugging Face Space: {space_url}")
        client = Client(space_url)

        print(f"[AI_IMAGE] Generating image for prompt: '{final_prompt}'")
        # Assume the Space has an endpoint named "/generate" that takes a single string prompt
        # Run the synchronous client.predict in a thread pool to avoid blocking the event loop
        result_path = await asyncio.to_thread(
            client.predict,
            final_prompt,
            api_name="/generate"
        )

        print(f"[AI_IMAGE] Image generated, temporary path: {result_path}")
        # Read the temporary file as bytes
        with open(result_path, "rb") as f:
            image_bytes = f.read()

        # Clean up the temporary file (optional)
        try:
            os.remove(result_path)
        except:
            pass

        return image_bytes

    except Exception as e:
        print(f"[AI_IMAGE] Error generating image with Hugging Face Space: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Hugging Face Space image generation failed: {str(e)}"
        )
def enhance_search_query(word: str) -> str:
    """
    Enhance search query to be more conceptual and avoid text-based images.
    Maps common words/greetings to descriptive photo search terms.
    """
    word_lower = word.lower().strip()

    # Common greetings and abstract concepts - make them more visual/conceptual
    concept_map = {
        'hello': 'people greeting handshake',
        'goodbye': 'person waving farewell',
        'bye': 'person waving goodbye',
        'thanks': 'grateful person thanking',
        'thank you': 'people expressing gratitude',
        'please': 'person asking politely',
        'sorry': 'person apologizing regretful',
        'yes': 'person nodding agreement',
        'no': 'person shaking head disagreement',
        'good morning': 'sunrise morning scene',
        'good night': 'night stars moon',
        'good afternoon': 'afternoon sunny day',
        'welcome': 'welcoming gesture open arms',
        'congratulations': 'people celebrating success',
    }

    # Check if it's in our concept map
    if word_lower in concept_map:
        return concept_map[word_lower]

    # For other words, keep them simple (concrete nouns work well as-is)
    # Add "photo of" to avoid text-based images
    return f"photo of {word}"

# Helper to get Pexels image bytes and photographer
def _generate_image_with_pexels(drill_text_catalan: str, custom_search_query: Optional[str] = None) -> (bytes, str):
    """
    Fetches an image from Pexels API and returns its content as bytes and photographer.
    """
    try:
        if custom_search_query:
            user_query = custom_search_query
            print(f"[IMAGE] Using custom search phrase: {user_query}")
            try:
                translated = translator_ca_to_en.translate(user_query)
                search_query = enhance_search_query(translated)
            except Exception as trans_error:
                print(f"[IMAGE] Translation failed: {trans_error}, using as-is")
                search_query = enhance_search_query(user_query)
        else:
            try:
                translated = translator_ca_to_en.translate(drill_text_catalan)
                search_query = enhance_search_query(translated)
            except Exception as trans_error:
                print(f"[IMAGE] Translation failed: {trans_error}, using original text")
                search_query = enhance_search_query(drill_text_catalan)

        api_url = "https://api.pexels.com/v1/search"
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": search_query, "per_page": 1, "orientation": "landscape"}

        print(f"[IMAGE] Searching Pexels for: {search_query}")
        search_response = requests.get(api_url, headers=headers, params=params, timeout=10)
        search_response.raise_for_status()
        search_data = search_response.json()

        if not search_data.get('photos') or len(search_data['photos']) == 0:
            raise HTTPException(status_code=404, detail=f"No images found for '{search_query}'")

        photo = search_data['photos'][0]
        photo_url = photo['src']['large']
        photographer_name = photo.get('photographer', 'Unknown')

        print(f"[IMAGE] Found photo by {photographer_name}, downloading from: {photo_url}")
        image_response = requests.get(photo_url, timeout=30)
        image_response.raise_for_status()

        return image_response.content, photographer_name

    except HTTPException:
        raise
    except Exception as e:
        print(f"[IMAGE] ERROR Pexels: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Pexels image generation failed: {str(e)}")

# ===================== Image Generation =====================
@app.post("/generate-image/{drill_id}")
async def generate_image(
    drill_id: int,
    use_ai: bool = Body(False),
    search_query: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")

    image_bytes = None
    photographer_info = "AI Generator"

    try:
        if use_ai and illustration_available():
            # Gemini draws the sentence in the deck's flashcard style (see illustrate.py);
            # `search_query` becomes a hint on what to draw, never the text itself.
            image_bytes = await asyncio.to_thread(generate_illustration, drill.text_catalan or search_query or "", search_query)
            photographer_info = "Gemini illustration"
        elif use_ai:
            # 1. NOM DEL REPOSITORI (New dedicated Space)
            PHOTO_SPACE = os.getenv("HUGGINGFACE_IMAGE_SPACE_URL", "josepabloucr/tachelhit-image-service")

            try:
                # 2. Traducció
                final_prompt = translator_ca_to_en.translate(search_query or drill.text_catalan)
                print(f"[AI_IMAGE] Connecting to Space: {PHOTO_SPACE} with prompt: {final_prompt}")

                # 3. Inicialització neta del client
                client = Client(PHOTO_SPACE)

                # 4. Predicció (Uses api_name="generate")
                result_path = await asyncio.to_thread(
                    _image_api_predict, client, final_prompt
                )

                with open(result_path, "rb") as f:
                    image_bytes = f.read()
            except Exception as e:
                print(f"[AI_IMAGE] Error en la crida a HF: {str(e)}")
                raise e # Deixem que el try/except exterior gestioni l'HTTP 500
        else:
            # Lògica de Pexels
            image_bytes, photographer_info = _generate_image_with_pexels(drill.text_catalan, search_query)

        # PUJADA A CLOUDINARY (Això faltava o estava mal tancat al teu fitxer)
        if image_bytes:
            result = cloudinary.uploader.upload(
                image_bytes,
                folder="tachelhit/images",
                public_id=f"img_{drill_id}_{int(datetime.utcnow().timestamp())}"
            )
            drill.image_url = normalize_media_url(result['secure_url'])
            db.commit()
            return {"image_url": drill.image_url, "photographer": photographer_info}

    except Exception as e:
        print(f"[IMAGE] ERROR: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ---- Bulk image fill (background job) --------------------------------------
# Auto-illustrate drills that lack an image, with Gemini's image model in the
# flashcard style (illustrate.py) when Gemini is configured, else the SD-Turbo
# Space. Grammar labels and bare interjections are skipped by default: there is
# no scene to draw for "sí sí sí".
_image_fill_job = {"running": False, "total": 0, "done": 0, "failed": 0, "skipped": 0, "current": ""}


def _image_api_predict(client, prompt):
    # The Space may expose the endpoint as //generate or /generate depending on
    # how api_name was registered by gradio; try the known variants.
    for name in ("//generate", "/generate", "generate"):
        try:
            return client.predict(prompt, api_name=name)
        except ValueError:
            continue
    return client.predict(prompt)


_GRAMMAR_WORDS = ("verb", "temps verbals", "gramàt", "gramat", "conjug", "pronom", "adjectiu", "preposici", "plural ", "singular ")


def _is_depictable(drill) -> bool:
    """Is there a scene to draw? A single concrete word ("carbassa", "vent") is the most
    drawable thing there is; what has no scene is a grammar label ("Verb comprar — temps
    verbals") or a chant of one word ("sí sí sí")."""
    text = (drill.text_catalan or "").strip()
    if not text:
        return False
    low = text.lower()
    if any(k in low for k in _GRAMMAR_WORDS):
        return False
    tag = (drill.tag or "").lower()
    if any(k in tag for k in ("gramat", "gramàt", "grammar")):
        return False
    lowered = [w.strip(".,!?¡¿…-").lower() for w in text.split()]
    lowered = [w for w in lowered if w]
    return not (len(lowered) >= 2 and len(set(lowered)) == 1)


def _run_image_fill(only_depictable: bool = True):
    import time as _t
    from sqlalchemy import or_ as _or
    db = SessionLocal()
    client = None
    try:
        drills = db.query(DrillModel).filter(
            _or(DrillModel.image_url == None, DrillModel.image_url == ""),  # noqa: E711
            DrillModel.text_catalan != None, DrillModel.text_catalan != "",  # noqa: E711
        ).all()
        _image_fill_job["total"] = len(drills)
        space = os.getenv("HUGGINGFACE_IMAGE_SPACE_URL", "josepabloucr/huggingface-image-space")
        for d in drills:
            if not _image_fill_job["running"]:
                break
            if only_depictable and not _is_depictable(d):
                _image_fill_job["skipped"] += 1
                continue
            _image_fill_job["current"] = (d.text_catalan or "")[:40]
            try:
                if illustration_available():
                    image_bytes = generate_illustration(d.text_catalan)
                else:
                    if client is None:
                        client = Client(space)
                    prompt = translator_ca_to_en.translate(d.text_catalan)
                    result_path = _image_api_predict(client, prompt)
                    with open(result_path, "rb") as f:
                        image_bytes = f.read()
                up = cloudinary.uploader.upload(
                    image_bytes, folder="tachelhit/images",
                    public_id=f"img_{d.id}_{int(datetime.utcnow().timestamp())}",
                )
                d.image_url = normalize_media_url(up["secure_url"])
                db.commit()
                _image_fill_job["done"] += 1
            except Exception as e:
                db.rollback()
                _image_fill_job["failed"] += 1
                print(f"[IMG_FILL] drill {d.id} failed: {e}")
            _t.sleep(0.4)
    finally:
        _image_fill_job["running"] = False
        _image_fill_job["current"] = ""
        db.close()


def _drill_meanings(d) -> Dict[str, str]:
    return {"català": d.text_catalan or "", "àrab": d.text_arabic or "", "anglès": getattr(d, "text_english", "") or ""}


def _check_drill_draft(d, db) -> Optional[dict]:
    """Run the meaning check on a drill's draft and store it. None = nothing to check."""
    if (d.text_tachelhit or "").strip() or not (d.text_tachelhit_suggested or "").strip():
        return None
    rec = check_draft_meaning(d.text_tachelhit_suggested, _drill_meanings(d))
    if rec is None:
        return None
    d.draft_check = json.dumps(rec, ensure_ascii=False)
    db.commit()
    return rec


@app.post("/drafts/check/{drill_id}")
def check_draft(drill_id: int, db: Session = Depends(get_db)):
    """Meaning check of one drill's machine draft against its known meaning."""
    d = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Drill not found")
    rec = _check_drill_draft(d, db)
    if rec is None:
        return {"drill_id": drill_id, "status": "nothing_to_check"}
    return {"drill_id": drill_id, **rec}


_draft_check_job = {"running": False, "total": 0, "done": 0, "failed": 0, "no": 0, "roughly": 0, "yes": 0}


def _run_draft_checks():
    db = SessionLocal()
    try:
        todo = [d for d in db.query(DrillModel).all()
                if not (d.text_tachelhit or "").strip() and (d.text_tachelhit_suggested or "").strip()
                and draft_status(d.draft_check, d.text_tachelhit_suggested) == "unchecked"]
        _draft_check_job["total"] = len(todo)
        for d in todo:
            if not _draft_check_job["running"]:
                break
            try:
                rec = _check_drill_draft(d, db)
                if rec:
                    _draft_check_job[rec["verdict"]] += 1
                _draft_check_job["done"] += 1
            except Exception as e:
                _draft_check_job["failed"] += 1
                print(f"[DRAFT-CHECK] drill {d.id} failed: {e}")
                db.rollback()
    finally:
        _draft_check_job["running"] = False
        db.close()


@app.post("/drafts/check-missing")
def check_missing_drafts():
    """Background: check every unchecked draft (drills with a machine draft and no speaker text)."""
    if _draft_check_job["running"]:
        return {"status": "already_running", **_draft_check_job}
    import threading
    for k in ("total", "done", "failed", "no", "roughly", "yes"):
        _draft_check_job[k] = 0
    _draft_check_job["running"] = True
    threading.Thread(target=_run_draft_checks, daemon=True).start()
    return {"status": "started"}


@app.get("/drafts/check-missing/status")
def check_missing_drafts_status():
    return dict(_draft_check_job)


@app.post("/images/fill-missing")
def fill_missing_images(only_depictable: bool = True):
    if _image_fill_job["running"]:
        return {"status": "already_running", **_image_fill_job}
    import threading
    for k in ("total", "done", "failed", "skipped"):
        _image_fill_job[k] = 0
    _image_fill_job["running"] = True
    threading.Thread(target=_run_image_fill, args=(only_depictable,), daemon=True).start()
    return {"status": "started", "only_depictable": only_depictable}


@app.get("/images/fill-missing/status")
def fill_missing_status():
    return dict(_image_fill_job)


@app.post("/images/fill-missing/stop")
def fill_missing_stop():
    _image_fill_job["running"] = False
    return {"status": "stopping"}


@app.get("/transliterate")
def transliterate(text: str = ""):
    """Berber phone-Latin (or academic Latin) -> its faces:
    {input, clean_latin, tifinagh, key}. Deterministic, no external service.
    The forms are suggestions to confirm, never gold — see transliteration.py."""
    from transliteration import to_forms
    return to_forms(text)


# ---- HuggingFace Space health (reliability) --------------------------------
# The AI features run on free HF Spaces that sleep after inactivity and wake
# slowly. Surfacing their state lets the UI say "waking up… ~30s" + offer to
# pre-warm, instead of a capture silently failing.
_HF_SPACES = {
    "asr": ("HUGGINGFACE_ASR_SPACE_URL", ASR_SPACE_DEFAULT),
    "tts": ("HUGGINGFACE_TTS_SPACE_URL", "Tamazight-NLP/TTS"),
    "translation": ("HUGGINGFACE_TRANSLATION_SPACE_URL", "https://huggingface.co/spaces/josepabloucr/Finetuned-Quantized-NLLB"),
    "ocr": ("HUGGINGFACE_OCR_SPACE_URL", ""),
    "image": ("HUGGINGFACE_IMAGE_SPACE_URL", "josepabloucr/huggingface-image-space"),
}


def _hf_space_url(space_id: str) -> str:
    """Normalize a Space id / URL to its runnable https://<sub>.hf.space/ URL."""
    s = (space_id or "").strip()
    if not s:
        return ""
    if ".hf.space" in s:
        return s if s.startswith("http") else "https://" + s
    m = re.search(r"huggingface\.co/spaces/([^/?#]+/[^/?#]+)", s)
    if m:
        s = m.group(1)
    sub = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return f"https://{sub}.hf.space/" if sub else ""


def _hf_space_state(space_id: str) -> dict:
    url = _hf_space_url(space_id)
    if not url:
        return {"state": "unset"}
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return {"state": "up"}
        if r.status_code == 503:
            return {"state": "waking"}
        # 401/404 to an unauthenticated probe usually means the Space is PRIVATE
        # (works via token from the backend) — don't cry wolf; flag separately.
        if r.status_code in (401, 403, 404):
            return {"state": "private_or_missing", "code": r.status_code}
        return {"state": "down", "code": r.status_code}
    except requests.exceptions.Timeout:
        # a hung request to a sleeping Space almost always means it's spinning up
        return {"state": "waking"}
    except Exception:
        return {"state": "down"}


@app.get("/health/spaces")
def health_spaces():
    """Reachability/state of each AI Space: up | waking | down | unset."""
    import concurrent.futures
    ids = {k: os.getenv(env, default) for k, (env, default) in _HF_SPACES.items()}
    out = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futs = {k: ex.submit(_hf_space_state, v) for k, v in ids.items()}
        for k, f in futs.items():
            try:
                out[k] = f.result(timeout=13)
            except Exception:
                out[k] = {"state": "waking"}
            out[k]["id"] = ids[k]
    return out


@app.post("/health/spaces/wake")
def wake_spaces(only: Optional[str] = None):
    """Fire-and-forget warm-up pings so sleeping Spaces start booting. Pass
    ?only=asr,translation to wake ONLY those — waking every Space at once can
    blow the free HuggingFace CPU quota (which only runs a few Spaces at a time)."""
    import threading
    keys = [k.strip() for k in (only or "").split(",") if k.strip() in _HF_SPACES]
    if not keys:
        keys = list(_HF_SPACES.keys())

    def _ping(u):
        try:
            requests.get(u, timeout=4)
        except Exception:
            pass

    woken = []
    for k in keys:
        env, default = _HF_SPACES[k]
        u = _hf_space_url(os.getenv(env, default))
        if u:
            threading.Thread(target=_ping, args=(u,), daemon=True).start()
            woken.append(k)
    return {"waking": woken}


@app.get("/upload-media/{drill_id}/{media_type}")
async def test_upload_endpoint(drill_id: int, media_type: str):
    print(f"[UPLOAD TEST] GET request for drill {drill_id}, media_type {media_type}")
    return {
        "message": "Upload endpoint is reachable",
        "method": "GET",
        "drill_id": drill_id,
        "media_type": media_type,
        "supported_methods": ["POST"]
    }

@app.post("/upload-media/{drill_id}/{media_type}")
async def upload_media(drill_id: int, media_type: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    print(f"[UPLOAD] Received POST upload request for drill {drill_id}, media_type {media_type}")
    print(f"[UPLOAD] Request method: POST")
    print(f"[UPLOAD] File name: {file.filename}")
    print(f"[UPLOAD] Content type: {file.content_type}")

    # Verificar que el método sea POST
    import inspect
    print(f"[UPLOAD] Current function: {inspect.currentframe().f_code.co_name}")
    if media_type not in ["audio", "video", "image"]:
        raise HTTPException(status_code=400, detail="Invalid media type")

    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")

    try:
        # Read file content
        content = await file.read()

        # Validar que el fitxer no estigui buit
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        # Check if Cloudinary is configured
        use_cloudinary = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))

        # Determinar l'extensió del fitxer
        if file.filename and "." in file.filename:
            ext = file.filename.split(".")[-1].lower()
        else:
            # Extensions per defecte segons el tipus de mitjà
            if media_type == "audio":
                ext = "webm"
            elif media_type == "video":
                ext = "mp4"
            else:  # image
                ext = "jpg"

        # Validar extensions permeses
        allowed_extensions = {
            "audio": ["webm", "mp4", "ogg", "wav", "m4a", "mp3", "aac"],
            "video": ["mp4", "webm", "mov", "avi", "m4v"],
            "image": ["jpg", "jpeg", "png", "gif", "webp"]
        }

        if ext not in allowed_extensions.get(media_type, []):
            raise HTTPException(
                status_code=400,
                detail=f"File extension .{ext} not allowed for {media_type}. Allowed: {allowed_extensions[media_type]}"
            )

        if use_cloudinary:
            # Upload to Cloudinary
            print(f"[UPLOAD] Uploading {media_type} to Cloudinary for drill {drill_id}")

            # Determine resource type
            resource_type = "video" if media_type in ["audio", "video"] else "image"

            # Per a àudio, utilitzar resource_type "video" a Cloudinary (també funciona per àudio)
            if media_type == "audio":
                resource_type = "video"

            # Upload to Cloudinary — blocking HTTP, so off the event loop (P4.5)
            result = await run_in_threadpool(
                cloudinary.uploader.upload,
                content,
                folder=f"tachelhit/{media_type}",
                public_id=f"{media_type}_{drill_id}_{int(datetime.utcnow().timestamp())}",
                resource_type=resource_type
            )

            url = result['secure_url']
            url = normalize_media_url(url)
            print(f"[UPLOAD] Cloudinary URL: {url}")
        else:
            # Fallback to local storage
            print(f"[UPLOAD] Uploading {media_type} locally for drill {drill_id}")
            filename = f"{media_type}_{drill_id}_{int(datetime.utcnow().timestamp())}.{ext}"
            dir_path = os.path.join(MEDIA_ROOT, media_type)
            os.makedirs(dir_path, exist_ok=True)  # Assegurar que el directori existeix
            file_path = os.path.join(dir_path, filename)

            with open(file_path, "wb") as f:
                f.write(content)

            url = f"/media/{media_type}/{filename}"
            url = normalize_media_url(url)

        # Update drill with media URL
        if media_type == "audio":
            drill.audio_url = url
        elif media_type == "video":
            drill.video_url = url
        elif media_type == "image":
            drill.image_url = url

        db.commit()
        return {"url": url}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[UPLOAD] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# ===================== TEST CRUD =====================
def _with_step_count(db: Session, tests):
    """Stamp each practice with how many steps it holds, for the response model.

    One grouped query for the lot. A practice that never got steps falls back to the length of
    its old flat list, so an unconverted one still reports what it has."""
    rows = tests if isinstance(tests, list) else [tests]
    sizes = practice_mod.practice_sizes(db, rows)
    for t in rows:
        t.step_count = sizes.get(t.id, 0)
    return tests

@app.get("/tests/", response_model=list[Test])
def get_tests(response: Response, since: Optional[str] = None, mine: bool = False,
              limit: Optional[int] = None, offset: Optional[int] = None,
              db: Session = Depends(get_db),
              user: Optional[UserModel] = Depends(get_current_user)):
    """List tests, newest first. Same `since`/`limit`/`offset`/X-Total-Count
    contract as GET /drills/ (no pagination unless limit or offset is sent).

    `mine=1` keeps only the practices the asking person may call theirs -- what «les meves
    llistes» is supposed to show, and what it did not: the screen listed everyone's."""
    query = db.query(TestModel)
    if mine:
        if not user:
            raise HTTPException(status_code=401, detail="mine=1 requires X-User-Token")
        ids = [t.id for t in practice_mod.my_practices(db, user)]
        query = query.filter(TestModel.id.in_(ids)) if ids else query.filter(sa_false())
    if since:
        query = query.filter(
            sa_func.coalesce(TestModel.updated_at, TestModel.date_created) >= _parse_since(since)
        )
    return _with_step_count(db, _paginate(query.order_by(TestModel.date_created.desc()),
                                         response, limit, offset))

@app.get("/tests/{test_id}", response_model=Test)
def get_test(test_id: int, db: Session = Depends(get_db)):
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return _with_step_count(db, test)

@app.post("/tests/", response_model=Test)
def create_test(test: TestCreate, db: Session = Depends(get_db),
                user: Optional[UserModel] = Depends(get_current_user)):
    """Make a practice. It belongs to whoever made it (#199): that is what «les meves llistes»
    is built on, and what decides later who may change it.

    A name is asked for BEFORE it is made, not after. Until 2026-10-23 a visitor without one got
    a practice that belonged to nobody -- and `may_change` reads an unclaimed thing as the
    administrator's, so every later save came back 403, it could not be renamed, it could not be
    deleted, and the work put into it was gone. Better a sentence asking for a name than a
    practice that cannot be used."""
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Una pràctica és d'algú: fes-te un nom al teu perfil (és gratis i triga un "
                   "moment) i la tindràs a «les meves llistes», per editar-la i refer-la quan vulguis.")
    db_test = TestModel(**test.model_dump())
    if not getattr(db_test, "created_by_user_id", None):
        db_test.created_by_user_id = user.id
    db.add(db_test)
    db.commit()
    db.refresh(db_test)
    # A practice made from a list of sentences starts as those sentences, one step each.
    try:
        steps = practice_steps.from_legacy(db_test)
        if steps:
            practice_steps.replace_steps(db, db_test.id, steps)
    except Exception as e:
        print(f"[PRACTICE] steps for test {db_test.id}: {e}")
    return _with_step_count(db, db_test)

@app.put("/tests/{test_id}", response_model=Test)
def update_test(test_id: int, update_data: TestUpdate, db: Session = Depends(get_db),
                user: Optional[UserModel] = Depends(get_current_user)):
    """Change a practice: its name, its description, whatever is sent. Whoever made it, or an
    admin -- the same rule as its steps and as a drill. Until 2026-10-22 ANY visitor could rename
    or empty anyone's practice."""
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    owner_or_admin(test, user, "pràctica")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(test, key, value)

    test.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(test)
    return _with_step_count(db, test)

@app.delete("/tests/{test_id}")
def delete_test(test_id: int, db: Session = Depends(get_db),
                user: Optional[UserModel] = Depends(get_current_user)):
    """Throw a practice away. Whoever made it, or an admin."""
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    owner_or_admin(test, user, "pràctica")
    # Els passos s'esborren aquí i no es deixen al `ON DELETE CASCADE` de la clau forana:
    # Postgres el fa, però SQLite no aplica les claus foranes si no s'ha activat
    # `PRAGMA foreign_keys=ON`, i no l'activem enlloc. En local i a les proves, doncs, els
    # passos sobrevivien a la seva pràctica — i com que SQLite reutilitza l'id més alt que
    # s'acaba d'esborrar, la pràctica següent naixia amb els passos de l'anterior.
    practice_steps.forget(db, test_id)
    db.delete(test)
    db.commit()
    return {"detail": "Deleted"}

# ===================== TEST ATTEMPT CRUD =====================
@app.get("/test-attempts/", response_model=list[TestAttempt])
def get_test_attempts(response: Response, test_id: Optional[int] = None, mine: bool = False,
                      limit: Optional[int] = None, offset: Optional[int] = None,
                      db: Session = Depends(get_db),
                      user: Optional[UserModel] = Depends(get_current_user)):
    """List attempts, newest first. `mine=1` keeps only the requesting user's
    (needs X-User-Token, P4.8). Pagination as GET /drills/."""
    query = db.query(TestAttemptModel)
    if test_id:
        query = query.filter(TestAttemptModel.test_id == test_id)
    if mine:
        if not user:
            raise HTTPException(status_code=401, detail="mine=1 requires X-User-Token")
        query = query.filter(TestAttemptModel.user_id == user.id)
    return _paginate(query.order_by(TestAttemptModel.date_taken.desc()), response, limit, offset)

@app.post("/test-attempts/", response_model=TestAttempt)
def create_test_attempt(attempt: TestAttemptCreate, db: Session = Depends(get_db),
                        user: Optional[UserModel] = Depends(get_current_user)):
    db_attempt = TestAttemptModel(**attempt.model_dump(), user_id=user.id if user else None)
    db.add(db_attempt)
    db.commit()
    db.refresh(db_attempt)
    return db_attempt

# ===================== TEST STATISTICS =====================
@app.get("/tests/{test_id}/steps")
def get_practice_steps(test_id: int, db: Session = Depends(get_db)):
    """The steps of a practice, in the order a learner meets them."""
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return {"test_id": test_id, "steps": practice_steps.steps_of(db, test_id),
            "kinds": {k: {"needs_drill": v[0], "asks": v[1]} for k, v in practice_steps.KINDS.items()}}


@app.put("/tests/{test_id}/steps")
def put_practice_steps(test_id: int, steps: List[dict] = Body(..., embed=True),
                       db: Session = Depends(get_db),
                       user: Optional[UserModel] = Depends(get_current_user)):
    """Rewrite a practice's steps in the order the editor sends. Whoever made the practice, or an
    admin: the same rule as a drill. Nothing is deleted until every step has been checked."""
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    owner_or_admin(test, user, "pràctica")
    try:
        return {"test_id": test_id, "steps": practice_steps.replace_steps(db, test_id, steps)}
    except practice_steps.StepError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tests/{test_id}/stats")
def get_test_stats(test_id: int, db: Session = Depends(get_db)):
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    attempts = db.query(TestAttemptModel).filter(TestAttemptModel.test_id == test_id).all()

    if not attempts:
        return {
            "total_attempts": 0,
            "average_score": 0,
            "completion_rate": 0,
            "average_time": 0
        }

    total_attempts = len(attempts)
    # Calculate average score, ignoring None values
    scores = [a.score for a in attempts if a.score is not None]
    average_score = sum(scores) / len(scores) if scores else 0
    # Determine passing attempts based on passing_score (if set)
    if test.passing_score is not None:
        passed_attempts = sum(1 for a in attempts if a.score is not None and a.score >= test.passing_score)
    else:
        # If no passing threshold, consider all attempts with a score as passed
        passed_attempts = sum(1 for a in attempts if a.score is not None)
    completion_rate = (passed_attempts / total_attempts) * 100 if total_attempts > 0 else 0
    # Average time, ignoring None values
    times = [a.time_taken_seconds for a in attempts if a.time_taken_seconds is not None]
    average_time = sum(times) / len(times) if times else 0

    return {
        "total_attempts": total_attempts,
        "average_score": round(average_score, 2),
        "completion_rate": round(completion_rate, 2),
        "average_time": round(average_time, 2),
        "passed_attempts": passed_attempts
    }
def call_huggingface_space(payload_data: list):
    """
    Calls the Hugging Face Space using the official Client.
    Handles queueing, polling, and downloading automatically.
    Returns the local path of the generated video.
    """
    print(f"[HF SPACE] 🚀 Initializing Client...")
    try:
        # 1. Connect to the Space (uses HUGGINGFACE_SPACE_URL from env)
        space_url = os.getenv("HUGGINGFACE_SPACE_URL")
        print(f"[HF SPACE] Using Space URL: {space_url}")

        if not space_url:
            raise ValueError("HUGGINGFACE_SPACE_URL environment variable not set")

        client = Client(space_url)
        print(f"[HF SPACE] Client connected successfully")

        print(f"[HF SPACE] ⏳ Submitting job to queue with payload: {payload_data[:2]}... (this may take 1-3 mins)")

        # 2. Submit the job. The client will wait until it's done.
        # We pass the arguments as a list using *payload_data
        result_path = client.predict(
            *payload_data,
            api_name="/predict"
        )

        print(f"[HF SPACE] ✅ Job complete! Video downloaded to: {result_path}")
        return result_path

    except Exception as e:
        print(f"[HF SPACE] 💥 Client Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Video Generation failed: {str(e)}")

def _set_job_status(db, job, status: str, **fields) -> None:
    """Best-effort status write for a tracked VideoProcessingJob (P4.6)."""
    if job is None:
        return
    try:
        job.status = status
        for k, v in fields.items():
            setattr(job, k, v)
        job.updated_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        print(f"[WORKER] Could not update job {getattr(job, 'id', '?')}: {e}")
        try:
            db.rollback()
        except Exception:
            pass

def background_video_vault(job_type: str, item_id: int, payload_data: list, job_id: Optional[int] = None):
    """
    Background worker. Now uploads the LOCALLY downloaded file from Gradio Client.
    When `job_id` is given, the VideoProcessingJob row tracks progress so
    GET /video-analysis/job/{id} can be polled (P4.6).
    """
    db = SessionLocal()
    job = None
    try:
        if job_id:
            job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
            _set_job_status(db, job, "IN_PROGRESS")
        # Step A: Call Hugging Face (Blocking call via Client)
        # This now returns a local file path like '/tmp/gradio/...'
        local_video_path = call_huggingface_space(payload_data)

        # Step B: Upload the LOCAL file to Cloudinary
        print(f"[WORKER] ☁️ Uploading local file to Cloudinary: {local_video_path}")
        upload_result = cloudinary.uploader.upload(
            local_video_path,
            folder=f"tachelhit/{job_type}s",
            resource_type="video",
            public_id=f"{job_type}_{item_id}_{int(datetime.utcnow().timestamp())}"
        )
        cloudinary_url = upload_result['secure_url']
        cloudinary_url = normalize_media_url(cloudinary_url)

        # Step C: Update Database
        if job_type == "short":
            drill = db.query(DrillModel).filter(DrillModel.id == item_id).first()
            if drill:
                drill.video_url = cloudinary_url
                new_short = YouTubeShortModel(
                    drill_id=item_id,
                    video_path=cloudinary_url,
                    text_catalan=drill.text_catalan,
                    text_tachelhit=drill.text_tachelhit
                )
                db.add(new_short)

        elif job_type == "demo":
            test = db.query(TestModel).filter(TestModel.id == item_id).first()
            if test:
                test.video_url = cloudinary_url
            print(f"[WORKER] Demo for Test {item_id} ready at: {cloudinary_url}")

        db.commit()
        print(f"[WORKER] ✅ Successfully vaulted {job_type} for ID {item_id}")
        _set_job_status(db, job, "COMPLETED",
                        processing_log=json.dumps({"video_url": cloudinary_url, "item_id": item_id}))

        # Cleanup the local temp file from Gradio Client
        if os.path.exists(local_video_path):
            os.remove(local_video_path)

    except Exception as e:
        print(f"[WORKER] ❌ Task Failed: {str(e)}")
        # Print full traceback to logs for debugging
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass
        _set_job_status(db, job, "FAILED", error_message=str(e)[:2000])
    finally:
        db.close()

def _new_render_job(db, kind: str, item_id: int) -> VideoProcessingJobModel:
    """Create the job row that a reel/demo render reports into (P4.6)."""
    job = VideoProcessingJobModel(kind=kind, status="PENDING",
                                  processing_log=json.dumps({"item_id": item_id}))
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

# ===================== YOUTUBE SHORTS =====================
@app.post("/generate-short/{drill_id}")
async def generate_short(drill_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")

    # Prepare Payload
    drill_data = {
        'text_catalan': drill.text_catalan,
        'text_tachelhit': drill.text_tachelhit,
        'text_arabic': drill.text_arabic,
        'image_url': drill.image_url,
        'audio_url': drill.audio_url,
        'audio_tts_url': drill.audio_tts_url  # <--- ADD THIS LINE
    }
    filename = f"short_{drill_id}_{int(datetime.now().timestamp())}.mp4"
    payload_data = ["short", json.dumps(drill_data), None, filename, 0]

    # 🚀 Start background task and return immediately (job id is pollable at
    # GET /video-analysis/job/{job_id})
    job = _new_render_job(db, "short", drill_id)
    background_tasks.add_task(background_video_vault, "short", drill_id, payload_data, job.id)

    return {"status": "processing", "job_id": job.id,
            "message": "Video generation started. It will appear in Cloudinary shortly."}
# ===================== DRILL PLAYER DEMO VIDEO =====================
@app.post("/generate-drillplayer-demo/{test_id}")
async def generate_drillplayer_demo(test_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    drill_ids = [int(id.strip()) for id in test.drill_ids.split(',') if id.strip()]
    drills = db.query(DrillModel).filter(DrillModel.id.in_(drill_ids)).all()

    drills_data = [{
        'id': d.id, 'text_catalan': d.text_catalan, 'text_tachelhit': d.text_tachelhit,
        'text_arabic': d.text_arabic,
        'image_url': d.image_url, 'audio_url': d.audio_url, 'audio_tts_url': d.audio_tts_url
    } for d in drills]

    filename = f"demo_test_{test_id}_{int(datetime.now().timestamp())}.mp4"
    payload_data = ["demo", None, json.dumps(drills_data), filename, test_id]

    # 🚀 Offload the heavy demo rendering to background
    job = _new_render_job(db, "demo", test_id)
    background_tasks.add_task(background_video_vault, "demo", test_id, payload_data, job.id)

    return {"status": "processing", "job_id": job.id,
            "message": "Demo video is being generated. This may take a few minutes."}

@app.get("/shorts/", response_model=list[YouTubeShort])
def get_shorts(response: Response, limit: Optional[int] = None, offset: Optional[int] = None,
               db: Session = Depends(get_db)):
    """List generated shorts, newest first. Pagination as GET /drills/."""
    return _paginate(db.query(YouTubeShortModel).order_by(YouTubeShortModel.date_created.desc()),
                     response, limit, offset)

@app.delete("/shorts/{short_id}")
def delete_short(short_id: int, db: Session = Depends(get_db)):
    short = db.query(YouTubeShortModel).filter(YouTubeShortModel.id == short_id).first()
    if not short:
        raise HTTPException(status_code=404, detail="Short not found")

    # Delete the underlying media asset (Cloudinary for vaulted shorts,
    # local media/ dir for legacy ones)
    try:
        if short.video_path and short.video_path.startswith("http"):
            public_id = extract_cloudinary_public_id(short.video_path)
            if public_id:
                cloudinary.uploader.destroy(public_id, resource_type="video")
                print(f"[API] Deleted Cloudinary asset: {public_id}")
        elif short.video_path:
            video_path = f"media/{short.video_path.replace('/media/', '')}"
            if os.path.exists(video_path):
                os.remove(video_path)
    except Exception as e:
        print(f"[API] Error deleting video file: {e}")

    db.delete(short)
    db.commit()
    return {"detail": "Deleted"}

# ===================== VIDEO PROCESSING =====================

# NOTE: the old placeholder /video-processing/* endpoints (simulated jobs that
# wrote fake res.cloudinary.com/demo/... URLs into real drills) were removed.
# The real pipeline lives under /video-analysis/*.

# Les eines de vídeo, carregades la PRIMERA VEGADA QUE ES FAN SERVIR i no en arrencar.
#
# `video_utils` arrossega moviepy i yt-dlp, i `correction_service` arrossega el client d'OpenAI.
# Importar-ho tot d'entrada costava 13 dels 18 segons que trigava `import main`, i aquests
# segons els paga qui obre l'app: el servei gratuït s'adorm als 15 minuts, i cada visita en
# desperta un de nou. La immensa majoria de peticions —el Mètode, la gramàtica, les frases— no
# toquen cap vídeo ni cap correcció, i ara no en paguen l'arrencada.
#
# Els noms es mantenen perquè les 19 crides no canvien: el que es crida és una funció que
# importa el mòdul de debò el primer cop i després li passa la pilota. La primera petició de
# vídeo paga els 8 segons; la resta, cap.
video_key = _lazy("video_utils", "video_key")
get_video_metadata = _lazy("video_utils", "get_video_metadata")
get_video_segments = _lazy("video_utils", "get_video_segments")
process_and_upload_segment = _lazy("video_utils", "process_and_upload_segment")
remote_process_and_upload_segment = _lazy("video_utils", "remote_process_and_upload_segment")
get_yt_dlp_cookie_file = _lazy("video_utils", "get_yt_dlp_cookie_file")
download_video_to_dir = _lazy("video_utils", "download_video_to_dir")
process_and_upload_audio_segment = _lazy("video_utils", "process_and_upload_audio_segment")
is_audio_file = _lazy("video_utils", "is_audio_file")
get_correction_service = _lazy("correction_service", "get_correction_service")

# All video uploads live under one parent dir so that (a) stale files from the
# two-step upload -> create-drills flow can be purged by age instead of leaking
# forever, and (b) create-drills can verify a client-supplied video_path really
# is one of our uploads and not an arbitrary server file.
UPLOADS_TMP_ROOT = os.path.join(tempfile.gettempdir(), "tachelhit_uploads")
os.makedirs(UPLOADS_TMP_ROOT, exist_ok=True)

def purge_stale_uploads(max_age_hours: float = 6):
    cutoff = datetime.utcnow().timestamp() - max_age_hours * 3600
    try:
        for name in os.listdir(UPLOADS_TMP_ROOT):
            path = os.path.join(UPLOADS_TMP_ROOT, name)
            try:
                if os.path.getmtime(path) < cutoff:
                    shutil.rmtree(path, ignore_errors=True)
                    print(f"[UPLOADS] Purged stale upload dir: {path}")
            except OSError:
                pass
    except OSError as e:
        print(f"[UPLOADS] Purge scan failed: {e}")

def is_managed_upload_path(path: str) -> bool:
    real = os.path.realpath(path)
    return real.startswith(os.path.realpath(UPLOADS_TMP_ROOT) + os.sep)

def extract_cloudinary_public_id(url: str) -> Optional[str]:
    """Derive the Cloudinary public_id from a delivery URL so the asset can be
    destroyed. Returns None for non-Cloudinary URLs."""
    try:
        if "res.cloudinary.com" not in url or "/upload/" not in url:
            return None
        path = url.split("/upload/", 1)[1].split("?")[0]
        parts = [p for p in path.split("/") if p]
        if parts and re.fullmatch(r"v\d+", parts[0]):
            parts = parts[1:]
        if not parts:
            return None
        return os.path.splitext("/".join(parts))[0]
    except Exception:
        return None

def resolve_hf_space_host(url: str) -> str:
    """Convert a huggingface.co/spaces/<owner>/<name> page URL into the direct
    <owner>-<name>.hf.space API host; anything else passes through unchanged."""
    if "huggingface.co/spaces/" in url:
        space_id = url.split("huggingface.co/spaces/")[-1].strip("/")
        owner, _, name = space_id.partition("/")
        if owner and name:
            sub = f"{owner}-{name}".lower().replace("_", "-").replace(".", "-")
            return f"https://{sub}.hf.space"
    return url.rstrip("/")

# ===================== NEW VIDEO ANALYSIS ENDPOINTS =====================

def process_video_analysis_task(job_id: int, video_path: str, tmp_dir: str, language: Optional[str] = None):
    """
    Background task to extract audio, upload to Cloudinary, call ASR Space, and update job.
    `language` is an optional Whisper language hint forwarded to the ASR Space.

    Deliberately a plain `def` (P4.5): it blocks on requests.post(timeout=600)
    to the ASR Space, and as a sync BackgroundTask FastAPI runs it in the
    threadpool instead of freezing the single-worker event loop for 10 min.
    """
    db = SessionLocal()
    try:
        job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
        if not job: return

        job.status = "IN_PROGRESS"
        db.commit()

        # 3. Call ASR Space (Direct Proxy)
        asr_space_url = os.getenv("HUGGINGFACE_ASR_SPACE_URL", ASR_SPACE_DEFAULT)
        if not asr_space_url:
            raise Exception("HUGGINGFACE_ASR_SPACE_URL not configured")

        # A huggingface.co/spaces/... page URL is not an API host; convert it
        asr_endpoint = resolve_hf_space_host(asr_space_url) + "/transcribe"
        print(f"[WORKER] Proxying video file for Job {job_id} to ASR Space...")

        hf_token = os.getenv("HUGGINGFACE_API_KEY")
        headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}

        with open(video_path, "rb") as f:
            resp = requests.post(
                asr_endpoint,
                files={"audio_file": (os.path.basename(video_path), f, "video/mp4")},
                data={"language": language} if language else None,
                headers=headers,
                timeout=600
            )

        resp.raise_for_status()
        asr_data = resp.json()

        segments = asr_data.get("segments", [])

        # Glossary normalization (word sound -> curated spelling) for
        # Tachelhit-ish sources; other languages pass through untouched
        if language in (None, "", "auto", "shi", "ber"):
            glossary = db.query(GlossaryItemModel).all()
            if glossary:
                pairs = [(g.word_sound, g.correct_spelling) for g in glossary]
                for seg in segments:
                    seg["text"] = apply_glossary(seg.get("text") or "", pairs)

        # 4. Save segments to DB
        for seg in segments:
            db_segment = VideoSegmentModel(
                job_id=job.id,
                segment_start_time=seg["start"],
                segment_end_time=seg["end"],
                text_original=seg["text"]
            )
            db.add(db_segment)

        job.status = "COMPLETED"
        job.processing_log = f"Successfully extracted {len(segments)} segments."
        db.commit()
        print(f"[WORKER] Job {job_id} completed successfully.")

    except Exception as e:
        print(f"[WORKER] Error in Job {job_id}: {str(e)}")
        job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
        if job:
            job.status = "FAILED"
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()

@app.post("/video-analysis/upload")
async def analyze_uploaded_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    subtitles: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Analyze an uploaded video file. If no subtitles are provided, it uses background ASR.
    Returns a Job ID for polling if ASR is needed.
    """
    print(f"[API] Received video upload request: {video.filename}")
    try:
        # Drop uploads older than the purge window, then create this upload's dir.
        # The file must outlive this request: /video-analysis/create-drills reads
        # it in a later request, so cleanup is age-based rather than immediate.
        purge_stale_uploads()
        tmp_dir = tempfile.mkdtemp(dir=UPLOADS_TMP_ROOT)
        # basename() strips any client-supplied path components (../ traversal)
        safe_filename = os.path.basename((video.filename or "").replace("\\", "/")) or "upload.mp4"
        video_path = os.path.join(tmp_dir, safe_filename)

        # Save video
        content = await video.read()
        with open(video_path, "wb") as f:
            f.write(content)

        # Create a Job entry
        job = VideoProcessingJobModel(
            source_filepath=video_path,
            status="PENDING",
            date_submitted=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        if subtitles:
            print(f"[API] Parsing provided subtitles immediately")
            sub_content = (await subtitles.read()).decode("utf-8")
            from video_utils import parse_vtt
            segments = parse_vtt(sub_content)

            for seg in segments:
                db_segment = VideoSegmentModel(
                    job_id=job.id,
                    segment_start_time=seg["start"],
                    segment_end_time=seg["end"],
                    text_original=seg["text"]
                )
                db.add(db_segment)

            job.status = "COMPLETED"
            db.commit()
            # NOTE: the temp video is intentionally kept — the client sends
            # video_path back to /video-analysis/create-drills for clipping.
            # purge_stale_uploads() reclaims it later.
            return {
                "job_id": job.id,
                "status": "COMPLETED",
                "title": video.filename,
                "video_path": video_path,
                "segments": segments
            }
        else:
            # AUTO-SEGMENTATION MODE (Background)
            print(f"[API] Starting background ASR task for Job {job.id}")
            background_tasks.add_task(process_video_analysis_task, job.id, video_path, tmp_dir)
            return {
                "job_id": job.id,
                "status": "PENDING",
                "title": video.filename,
                "video_path": video_path,
                "message": "Video uploaded. Background ASR analysis started."
            }

    except Exception as e:
        print(f"[API] ERROR in analyze_uploaded_video: {str(e)}")
        # Cleanup on error
        try:
            if 'tmp_dir' in locals() and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
                print(f"[API] Cleaned up temp directory on error: {tmp_dir}")
        except Exception as cleanup_e:
            print(f"[API] Error during cleanup: {cleanup_e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/video-analysis/job/{job_id}")
def get_video_analysis_job_status(job_id: int, db: Session = Depends(get_db)):
    """
    Polling endpoint for video analysis jobs.
    """
    job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Load segments
    segments = []
    if job.status == "COMPLETED":
        for seg in job.segments:
            segments.append({
                "start": seg.segment_start_time,
                "end": seg.segment_end_time,
                "text": seg.text_original
            })

    # Auto-pipeline jobs record their created drill ids in processing_log;
    # reel/demo render jobs (P4.6) record the finished video_url there.
    drills_created = None
    media_errors = None
    video_url = None
    if job.processing_log:
        try:
            log = json.loads(job.processing_log)
            if isinstance(log, dict):
                drills_created = log.get("drills_created")
                media_errors = log.get("media_errors")
                video_url = log.get("video_url")
        except (ValueError, TypeError):
            pass

    return {
        "id": job.id,
        "kind": getattr(job, "kind", None),
        "status": job.status,
        "error_message": job.error_message,
        "segments": segments,
        "drills_created": drills_created,
        "media_errors": media_errors,
        "video_url": video_url,
    }

@app.post("/video-analysis/analyze")
async def analyze_video(
    url: str = Body(...),
    cookies: Optional[str] = Body(None)
):
    """
    Analyze a YouTube URL to get metadata and available subtitles/captions.
    """
    try:
        # Get metadata
        info = get_video_metadata(url, cookies_str=cookies)

        # Determine subtitle language to use
        available_subs = info.get('subtitles', {})
        available_auto = info.get('automatic_captions', {})

        # Priority: Arabic (ar), French (fr), English (en), Spanish (es), Berber (shi)
        lang_priority = ['ar', 'fr', 'en', 'es', 'shi', 'ca']
        lang_to_use = None

        # Check standard subtitles first
        for lang in lang_priority:
            if lang in available_subs:
                lang_to_use = lang
                break

        # Then check automatic captions
        if not lang_to_use:
            for lang in lang_priority:
                if lang in available_auto:
                    lang_to_use = lang
                    break

        # Fallback to the first available if none of the priority languages exist
        if not lang_to_use:
            if available_subs:
                lang_to_use = list(available_subs.keys())[0]
            elif available_auto:
                lang_to_use = list(available_auto.keys())[0]

        if not lang_to_use:
            return {
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "segments": [],
                "message": "No subtitles or captions found for this video."
            }

        # Get segments
        segments = get_video_segments(url, lang_to_use, cookies_str=cookies)

        return {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "original_language": lang_to_use,
            "segments": segments
        }
    except Exception as e:
        print(f"[API] Error in analyze_video: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/video-analysis/import-url")
async def import_video_from_url(
    background_tasks: BackgroundTasks,
    url: str = Body(...),
    cookies: Optional[str] = Body(None),
    language: Optional[str] = Body(None),
    audio_only: Optional[bool] = Body(False),
    db: Session = Depends(get_db)
):
    """
    Server-side capture for any yt-dlp-supported site (YouTube, Instagram,
    TikTok, podcasts, ...): downloads the media into the managed uploads dir,
    then reuses the local-file pipeline — platform subtitles when available,
    background Whisper ASR otherwise. Because the file ends up local,
    create-drills clips it directly (no remote YouTube-only clip path, no
    repeat bot checks). audio_only grabs just the audio track (podcasts,
    voice content) and yields audio drills.
    """
    tmp_dir = None
    try:
        purge_stale_uploads()
        tmp_dir = tempfile.mkdtemp(dir=UPLOADS_TMP_ROOT)
        print(f"[IMPORT-URL] Downloading {url} (audio_only={audio_only}) ...")
        video_path, info = await asyncio.to_thread(download_video_to_dir, url, tmp_dir, cookies, bool(audio_only))

        job = VideoProcessingJobModel(
            source_url=url,
            source_filepath=video_path,
            status="PENDING",
            date_submitted=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        meta = {
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
        }

        # Cheap path first: platform-provided subtitles/captions
        segments = []
        lang_to_use = None
        try:
            subs_langs = list((info.get('subtitles') or {}).keys()) + \
                         list((info.get('automatic_captions') or {}).keys())
            lang_priority = ([language] if language else []) + ['shi', 'ber', 'ar', 'ca', 'fr', 'es', 'en']
            lang_to_use = next((l for l in lang_priority if l and l in subs_langs), None)
            if lang_to_use:
                segments = get_video_segments(url, lang_to_use, cookies_str=cookies)
        except Exception as sub_err:
            print(f"[IMPORT-URL] Subtitle fetch failed, falling back to ASR: {sub_err}")

        if segments:
            for seg in segments:
                db.add(VideoSegmentModel(
                    job_id=job.id,
                    segment_start_time=seg["start"],
                    segment_end_time=seg["end"],
                    text_original=seg["text"]
                ))
            job.status = "COMPLETED"
            db.commit()
            return {
                **meta,
                "job_id": job.id,
                "status": "COMPLETED",
                "original_language": lang_to_use or language or "auto",
                "video_path": video_path,
                "segments": segments
            }

        # No usable subtitles: transcribe the downloaded file with Whisper
        print(f"[IMPORT-URL] No subtitles found; starting background ASR for job {job.id}")
        background_tasks.add_task(process_video_analysis_task, job.id, video_path, tmp_dir, language)
        return {
            **meta,
            "job_id": job.id,
            "status": "PENDING",
            "original_language": language or "auto",
            "video_path": video_path,
            "message": "Video downloaded. Background transcription started."
        }

    except Exception as e:
        print(f"[IMPORT-URL] ERROR: {e}")
        traceback.print_exc()
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))

async def auto_drills_pipeline_task(job_id: int, url: Optional[str], video_path: str, tmp_dir: str,
                                    language: Optional[str], tag: Optional[str],
                                    apply_correction: bool, has_segments: bool,
                                    lyrics: Optional[str] = None, generate_reels: bool = False,
                                    meta: Optional[Dict[str, Any]] = None):
    # meta: {"title", "channel", "playlist", "license"} of the source, for the credit line
    meta = {k: (v or "").strip() for k, v in (meta or {}).items() if isinstance(v, str)}
    if not tag and meta.get("title"):
        tag = meta["title"][:60]  # catalogue by video when the user gave no tag
    variety = meta.get("variety") if meta.get("variety") in _VARIETY_CODES else None
    """
    Fully server-side capture pipeline: (ASR if needed) -> correction ->
    translation into all drill languages -> drill creation with media clips.
    Survives the user closing the page; progress is exposed through the job's
    status (TRANSCRIBING / CORRECTING / TRANSLATING / CREATING_DRILLS) and the
    final drill ids land in processing_log as JSON.
    """
    db = SessionLocal()
    try:
        job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
        if not job:
            return
        if not variety and meta.get("channel"):
            # Same channel, same variety: reuse what earlier captures were labelled with.
            prev = (db.query(DrillModel.variety).filter(DrillModel.source_channel == meta["channel"],
                                                          DrillModel.variety.isnot(None)).first())
            if prev and prev[0] in _VARIETY_CODES:
                variety = prev[0]
                print(f"[AUTO] variety {variety!r} inherited from earlier captures of {meta['channel']!r}")

        # Phase 1: no captions -> read the lesson text off the frames first
        # (letters / words burned into the picture); only if the frames carry no
        # lesson text do we fall back to speech recognition.
        lesson_segments: List[Dict[str, Any]] = []
        lesson_lines_untimed: List[Dict[str, Any]] = []
        page_mode = False
        # With lyrics given, the lines are known and only their TIMES are needed: those
        # come from speech recognition. The frame reader would return the lesson text
        # with no times for clips that show no text (a speaker on camera), and the
        # drills would end up text-only.
        if not has_segments and not is_audio_file(video_path) and not (lyrics and lyrics.strip()):
            job.status = "READING_FRAMES"
            db.commit()
            try:
                probe_frames = await asyncio.to_thread(extract_frames, video_path, os.path.join(tmp_dir, "probe"), 10.0, 640)
                mode = await asyncio.to_thread(detect_text_mode, probe_frames) if probe_frames else "none"
                print(f"[AUTO] on-screen text mode: {mode}")
                if mode == "page":
                    # A narrated page: narration ASR + the page frame give known units with
                    # their meaning; forced alignment gives their times; drills are DRAFTS.
                    page_lines = await asyncio.to_thread(read_page_text, video_path, tmp_dir)
                    if page_lines:
                        lyrics = "\n".join(page_lines)
                        page_mode = True
                        print(f"[AUTO] page text: {len(page_lines)} units -> aligned like lyrics, as drafts")
                if mode == "subtitles":
                    lesson_segments = await asyncio.to_thread(read_burned_subtitles, video_path, tmp_dir)
                if not lesson_segments and not (lyrics and lyrics.strip()):
                    lesson_segments = await asyncio.to_thread(read_onscreen_vocabulary, video_path, tmp_dir,
                                                              2.0, 12, meta.get("channel"))
            except Exception as e:
                print(f"[LESSON] frame reading failed: {e}")
            if lesson_segments:
                lesson_segments = await asyncio.to_thread(keep_amazigh_lines, lesson_segments)
            if lesson_segments and not any(seg.get("start") is not None for seg in lesson_segments):
                # A narrated lesson (a presenter on camera, words flashed now and then): the
                # lines are known from the audio but the frames gave no times. Speech
                # recognition gives the times; the lesson lines are laid on them below.
                print(f"[LESSON] {len(lesson_segments)} lines heard, none timed on screen -> times from ASR")
                lesson_lines_untimed = lesson_segments
                lesson_segments = []
            if lesson_segments:
                for seg in lesson_segments:
                    if seg.get("start") is None:
                        continue  # spoken but never shown: a text-only drill, no section to clip
                    db.add(VideoSegmentModel(job_id=job.id, segment_start_time=seg["start"],
                                             segment_end_time=seg["end"], text_original=seg["text"]))
                job.status = "COMPLETED"
                db.commit()
                has_segments = True
        aligned_segments: List[Dict] = []
        if not has_segments and lyrics and lyrics.strip():
            # Known lines: forced alignment gives their times directly (no machine
            # listening, no fuzzy match). Falls back to the transcribe path below.
            pairs = []
            for l in (x.strip() for x in lyrics.splitlines() if x.strip()):
                a, b = (l.split(" | ", 1) + [None])[:2] if " | " in l else (l, None)
                pairs.append((a.strip(), (b or "").strip() or None))
            timed = await asyncio.to_thread(_align_known_lines, video_path, [a for a, _ in pairs])
            if timed:
                for seg, (_, gloss) in zip(timed, pairs):
                    if gloss:
                        seg["gloss"], seg["gloss_lang"] = gloss, "ca"
                aligned_segments = timed
                print(f"[ALIGN] {len(timed)} lyric lines timed by forced alignment")
        elif not has_segments and lesson_lines_untimed:
            timed = await asyncio.to_thread(_align_known_lines, video_path,
                                            [it.get("tifinagh") or it.get("text") or "" for it in lesson_lines_untimed])
            if timed:
                items = [it for it in lesson_lines_untimed if (it.get("tifinagh") or it.get("text") or "").strip()]
                for seg, it in zip(timed, items):
                    for k in ("latin", "tifinagh", "gloss", "gloss_lang", "kind"):
                        if it.get(k):
                            seg[k] = it[k]
                aligned_segments = timed
                lesson_lines_untimed = []
                print(f"[ALIGN] {len(timed)} lesson lines timed by forced alignment")
        if not has_segments and not aligned_segments:
            job.status = "TRANSCRIBING"
            db.commit()
            await asyncio.to_thread(process_video_analysis_task, job_id, video_path, tmp_dir, language)
            db.expire_all()
            job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
            if not job or job.status != "COMPLETED":
                return  # ASR failed; its task already recorded the error

        segments = []
        if lesson_segments:
            segments = lesson_segments
            effective_source = "shi" if language in (None, "", "auto") else language
        elif aligned_segments:
            segments = aligned_segments
        else:
            db.expire_all()
            job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
            for s_ in job.segments:
                text_, gloss_, gloss_lang_ = split_bilingual_cue(s_.text_original) if has_segments else ((s_.text_original or ""), None, None)
                segments.append({
                    "start": s_.segment_start_time,
                    "end": s_.segment_end_time,
                    "text": text_,
                    "gloss": gloss_,            # e.g. "horse" — translated instead of the Tamazight
                    "gloss_lang": gloss_lang_,  # "en"
                })

        if lesson_lines_untimed and segments:
            segments = _attach_lesson_lines(segments, lesson_lines_untimed)

        if not segments:
            job.status = "FAILED"
            job.error_message = "No segments found to build drills from."
            db.commit()
            return

        effective_source = language if language not in (None, "", "auto") else "shi"
        src_name = LANGUAGE_CODE_MAP.get(effective_source, effective_source)

        # Song mode: replace ASR guesses with the provided lyric lines while
        # keeping the ASR timestamps; skip dataset correction (lyrics are truth)
        if lyrics and lyrics.strip():
            if not aligned_segments:
                segments = _align_lyrics_lines(segments, lyrics)
            apply_correction = False

        # Junk guard on the RAW transcript. It must run before correction: the
        # correction layer rewrites hallucinated English into Tachelhit-looking
        # text that no heuristic can catch afterwards (prod job 20, 2026-10-17).
        for seg in segments:
            if seg.get("gloss"):
                continue  # human caption with a gloss: trusted
            _j = looks_like_junk_asr(seg.get("text"), attested=effective_source in ("shi", "ber"))
            if _j:
                seg["junk"] = _j
                print(f"[AUTO] junk segment ({_j}), not corrected/translated: {str(seg.get('text'))[:60]!r}")

        # Phase 2: correction layer (Tachelhit-ish sources only; ASR output only —
        # human captions are better than the corrector)
        if apply_correction and not has_segments and effective_source in ("shi", "ber"):
            job.status = "CORRECTING"
            db.commit()
            ds = db.query(DrillModel).filter(DrillModel.is_correction_dataset == True).all()
            if not ds:
                ds = db.query(DrillModel).filter(
                    DrillModel.text_tachelhit != None,
                    DrillModel.text_tachelhit != ''
                ).limit(100).all()
            phrases = [d.text_tachelhit for d in ds if d.text_tachelhit]
            svc = get_correction_service()
            for seg in segments:
                text = (seg.get("text") or "").strip()
                if text and not seg.get("junk"):
                    try:
                        corrected, _ = await asyncio.to_thread(svc.correct_transcription, text, phrases)
                        seg["text"] = corrected
                    except Exception as e:
                        print(f"[AUTO] Correction failed for a segment: {e}")

        # Phase 3: translate into every drill language the source isn't
        job.status = "TRANSLATING"
        db.commit()
        # Captioned glosses ("horse") translate far better than the Tamazight word
        # through NLLB, and all of them go in ONE Gemini call; the Tamazight line
        # is kept verbatim.
        glossed = [seg for seg in segments if (seg.get("gloss") or "").strip() and not seg.get("junk")]
        if glossed:
            gloss_src = LANGUAGE_CODE_MAP.get(glossed[0].get("gloss_lang") or "en", "English")
            table = await asyncio.to_thread(translate_glosses, [seg["gloss"].strip() for seg in glossed], gloss_src)
            for seg in glossed:
                tr = table.get(seg["gloss"].strip(), {})
                seg["text_tachelhit"] = (seg.get("text") or "").strip()
                seg["text_catalan"] = tr.get("ca") or (seg["gloss"] if gloss_src == "Catalan" else None)
                seg["text_arabic"] = tr.get("ar") or (seg["gloss"] if gloss_src == "Modern Standard Arabic" else None)
        foreign = effective_source not in ("shi", "ber")
        plain = [seg for seg in segments if (seg.get("text") or "").strip() and not seg.get("junk") and not seg.get("gloss")]
        if foreign and plain:
            # Foreign captions (e.g. a story subtitled in Arabic): Catalan/Arabic in
            # one Gemini batch; machine Tachelhit is only ever a DRAFT suggestion.
            table = await asyncio.to_thread(translate_glosses, [seg["text"].strip() for seg in plain], src_name,
                                            tuple(t for t in ("ca", "ar") if LANGUAGE_CODE_MAP.get(t) != src_name))
            for seg in plain:
                tr = table.get(seg["text"].strip(), {})
                if "ca" in tr:
                    seg["text_catalan"] = tr["ca"]
                if "ar" in tr:
                    seg["text_arabic"] = tr["ar"]
        if foreign and plain and has_segments and os.getenv("NARRATION_DRAFTS", "1") != "0":
            # What is actually SPOKEN (draft): transcribe the narration per cue, with the
            # caption as the meaning anchor. Tamazight ASR is not solved (on the hedgehog
            # story 9 of 14 drafts were unrelated to the Arabic), so the draft is written
            # as a machine listening bracket "[? …]" in the suggestion field — the same
            # convention as tools/review_heard.py — and never as the Latin form: the
            # verification queue then offers it to a speaker as a one-tap option.
            # Disable with NARRATION_DRAFTS=0.
            try:
                spoken = await asyncio.to_thread(transcribe_narration, video_path, tmp_dir, plain, src_name)
                for i, seg in enumerate(plain):
                    heard = (spoken.get(i) or {}).get("latin") or (spoken.get(i) or {}).get("tifinagh") or ""
                    heard = " ".join(heard.split())
                    if heard and not any(c in heard for c in '{}"[]'):
                        seg["text_tachelhit_suggested"] = f"[? {heard}]"
                print(f"[NARRATION] {len(spoken)}/{len(plain)} cues got a spoken-Tamazight draft")
            except Exception as e:
                print(f"[NARRATION] skipped: {e}")
        for seg in plain:
            text = seg["text"].strip()
            for tgt, field in TRANSLATE_TARGET_FIELDS.items():
                if LANGUAGE_CODE_MAP.get(tgt) == src_name or (foreign and seg.get(field)):
                    continue
                if foreign and field == "text_tachelhit":
                    field = "text_tachelhit_suggested"   # draft for a speaker to confirm
                    if seg.get(field):
                        continue
                try:
                    seg[field] = await asyncio.to_thread(
                        translate_with_hf, text, src_name, LANGUAGE_CODE_MAP[tgt]
                    )
                except Exception as e:
                    print(f"[AUTO] Translation ({tgt}) failed for a segment: {e}")

        # A chorus repeats: one drill per distinct line (the first occurrence keeps its clip).
        segments = dedupe_repeated_lines(segments)
        if page_mode:
            segments = page_segments_to_drafts(segments)

        # Phase 4: create drills with clipped media
        job.status = "CREATING_DRILLS"
        db.commit()
        drills_created = []
        media_errors = []
        audio_src = is_audio_file(video_path)
        _prev_text = None
        # When the capture located the segments on the timeline (subtitles / on-screen
        # vocabulary), a segment WITHOUT a position is a word the model heard but could
        # not place: it would become a drill with no clip at all (lessons 04/05/06/12 on
        # 2026-10-18 each produced one, sometimes with the wrong letter). Drop those; a
        # pure audio transcript (nothing timed) keeps its text-only drills as before.
        for seg in segments:
            original_text = seg.get("text")
            # (untimed segments are kept: a text drill with a synthetic voice, see below)
            drill_tachelhit = seg.get("text_tachelhit") or (original_text if effective_source in ("shi", "ber") else None)
            drill_arabic = seg.get("text_arabic") or (original_text if effective_source == "ar" else None)

            # Skip empty segments (no text in any language) — nothing to learn.
            if not (drill_tachelhit or drill_arabic or seg.get("text_catalan") or seg.get("text_tachelhit_suggested")):
                continue
            _junk = seg.get("junk") or looks_like_junk_asr(drill_tachelhit, attested=effective_source in ("shi", "ber"))
            if _junk:
                print(f"[AutoDrills] skipping junk segment ({_junk}): {str(drill_tachelhit)[:60]!r}")
                media_errors.append(f"segment skipped ({_junk})")
                continue
            # Whisper on music/silence repeats one sentence for every window
            # (job 20: 4 identical "I can't bear to fall asleep"). One drill is
            # enough for identical consecutive text.
            _key = " ".join(str(original_text or drill_tachelhit or "").lower().split())
            if _key and _key == _prev_text:
                print(f"[AutoDrills] skipping repeated segment: {_key[:60]!r}")
                media_errors.append("segment skipped (repeat of previous)")
                continue
            _prev_text = _key

            if seg.get("kind") == "subtitle" and (seg.get("lines") or {}).get("ar") and not drill_arabic:
                drill_arabic = seg["lines"]["ar"]  # the video's own Arabic line beats a translation
            db_drill = DrillModel(
                text_catalan=seg.get("text_catalan"),
                text_tachelhit=drill_tachelhit,
                text_arabic=drill_arabic,
                text_tachelhit_latin=seg.get("latin") or None,
                text_tachelhit_suggested=seg.get("text_tachelhit_suggested"),
                tag=tag or "auto_capture",
                author="Auto Capture",
                source_url=url,
                source_title=meta.get("title") or None,
                source_channel=meta.get("channel") or None,
                source_playlist=meta.get("playlist") or None,
                license=meta.get("license") or ("youtube-standard" if url and "youtu" in url else None),
                variety=variety,
                # provenance: which seconds of the source this clip comes from
                video_start_time=seg.get("start"),
                video_end_time=seg.get("end"),
            )
            db.add(db_drill)
            db.commit()
            db.refresh(db_drill)
            if (seg.get("text_tachelhit_suggested") or "").strip() and not drill_tachelhit:
                # a machine listening: check it against the meaning before anyone learns from it
                try:
                    await asyncio.to_thread(_check_drill_draft, db_drill, db)
                except Exception as chk_err:
                    print(f"[DRAFT-CHECK] drill {db_drill.id}: {chk_err}")
            # Count the drill now — a text drill is valid even if media clipping
            # fails; the audio/video clip is best-effort enrichment on top.
            drills_created.append(db_drill.id)
            if drill_tachelhit and os.getenv("TTS_PREFILL", "1") != "0":
                # confirmed words (a subtitle track, a known lesson line): the synthetic voice is
                # made now and stored, so the player never has to wait for it
                await asyncio.to_thread(prefill_tts, db_drill, db)
            try:
                if seg.get("no_media") or seg.get("start") is None:
                    media_errors.append(f"{seg.get('latin') or seg.get('text')}: spoken but not shown on screen (no clip)")
                    # No section of the source to cut: give the text a synthetic Tamazight
                    # voice so the drill is still playable (marked synthetic in the player).
                    if drill_tachelhit:
                        try:
                            db_drill.audio_tts_shi_url = await asyncio.to_thread(generate_tachelhit_tts_hf, drill_tachelhit, db_drill.id)
                        except Exception as tts_err:
                            print(f"[AUTO] synthetic voice failed for drill {db_drill.id}: {tts_err}")
                    db.commit()
                    continue
                if audio_src:
                    res = await asyncio.to_thread(process_and_upload_audio_segment, video_path, seg["start"], seg["end"], db_drill.id)
                    db_drill.audio_url = normalize_media_url(res["audio_url"])
                else:
                    res = await asyncio.to_thread(process_and_upload_segment, video_path, seg["start"], seg["end"], db_drill.id)
                    db_drill.video_url = normalize_media_url(res["video_url"])
                    db_drill.image_url = normalize_media_url(res["image_url"])
                try:
                    db_drill.audio_tts_url = generate_catalan_tts(seg.get("text_catalan"), db_drill.id)
                except Exception:
                    pass
                db.commit()
            except Exception as e:
                # Keep the text drill; record why the clip failed so it's visible.
                if len(media_errors) < 3:
                    media_errors.append(f"{type(e).__name__}: {str(e)[:200]}")
                print(f"[AUTO] Media clipping failed for drill {db_drill.id}: {e}")
                db.rollback()

        # Phase 5 (optional): render a vertical reel for every created drill
        if generate_reels and drills_created:
            job.status = "GENERATING_REELS"
            db.commit()
            for did in drills_created:
                try:
                    d = db.query(DrillModel).filter(DrillModel.id == did).first()
                    if not d:
                        continue
                    drill_data = {
                        'text_catalan': d.text_catalan,
                        'text_tachelhit': d.text_tachelhit,
                        'text_arabic': d.text_arabic,
                        'image_url': d.image_url,
                        'audio_url': d.audio_url,
                        'audio_tts_url': d.audio_tts_url
                    }
                    filename = f"short_{did}_{int(datetime.utcnow().timestamp())}.mp4"
                    payload_data = ["short", json.dumps(drill_data), None, filename, 0]
                    await asyncio.to_thread(background_video_vault, "short", did, payload_data)
                except Exception as reel_err:
                    print(f"[AUTO] Reel generation failed for drill {did}: {reel_err}")

        job.status = "COMPLETED"
        job.processing_log = json.dumps({"drills_created": drills_created, "media_errors": media_errors})
        db.commit()
        print(f"[AUTO] Job {job_id}: created {len(drills_created)} drills, {len(media_errors)} media errors (reels={generate_reels}).")

    except Exception as e:
        print(f"[AUTO] Pipeline error in job {job_id}: {e}")
        traceback.print_exc()
        try:
            job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
            if job:
                job.status = "FAILED"
                job.error_message = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()

@app.post("/video-analysis/auto-drills")
async def auto_drills_from_url(
    background_tasks: BackgroundTasks,
    url: str = Body(...),
    cookies: Optional[str] = Body(None),
    language: Optional[str] = Body(None),
    audio_only: Optional[bool] = Body(False),
    tag: Optional[str] = Body(None),
    apply_correction: Optional[bool] = Body(True),
    lyrics: Optional[str] = Body(None),
    generate_reels: Optional[bool] = Body(False),
    db: Session = Depends(get_db)
):
    """
    One-shot capture: download -> transcribe -> (align lyrics) -> correct ->
    translate -> create drills -> (render reels), all server-side in the
    background. Returns a job_id to poll via /video-analysis/job/{id}; the
    final response there carries drills_created.
    """
    tmp_dir = None
    try:
        purge_stale_uploads()
        tmp_dir = tempfile.mkdtemp(dir=UPLOADS_TMP_ROOT)
        print(f"[AUTO] Downloading {url} (audio_only={audio_only}) ...")
        video_path, info = await asyncio.to_thread(download_video_to_dir, url, tmp_dir, cookies, bool(audio_only))

        job = VideoProcessingJobModel(
            source_url=url,
            source_filepath=video_path,
            status="PENDING",
            date_submitted=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Platform subtitles fast path (same as import-url)
        segments = []
        lang_to_use = None
        try:
            subs_langs = list((info.get('subtitles') or {}).keys()) + \
                         list((info.get('automatic_captions') or {}).keys())
            lang_priority = ([language] if language else []) + ['shi', 'ber', 'ar', 'ca', 'fr', 'es', 'en']
            lang_to_use = next((l for l in lang_priority if l and l in subs_langs), None)
            if lang_to_use:
                segments = get_video_segments(url, lang_to_use, cookies_str=cookies)
        except Exception as sub_err:
            print(f"[AUTO] Subtitle fetch failed, will use ASR: {sub_err}")

        if segments:
            for seg in segments:
                db.add(VideoSegmentModel(
                    job_id=job.id,
                    segment_start_time=seg["start"],
                    segment_end_time=seg["end"],
                    text_original=cue_text_for_storage(seg)
                ))
            db.commit()

        background_tasks.add_task(
            auto_drills_pipeline_task,
            job.id, url, video_path, tmp_dir,
            lang_to_use or language, tag, bool(apply_correction), bool(segments),
            lyrics, bool(generate_reels),
            {"title": (info or {}).get("title"), "channel": (info or {}).get("channel") or (info or {}).get("uploader"),
             "playlist": (info or {}).get("playlist_title"), "license": (info or {}).get("license")},
        )

        return {
            "job_id": job.id,
            "status": "PENDING",
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "message": "Auto pipeline started. Poll /video-analysis/job/{job_id} until drills_created appears."
        }
    except Exception as e:
        print(f"[AUTO] ERROR: {e}")
        traceback.print_exc()
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/video-analysis/auto-drills-upload")
async def auto_drills_from_upload(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    language: Optional[str] = Form(None),
    tag: Optional[str] = Form(None),
    apply_correction: Optional[bool] = Form(True),
    lyrics: Optional[str] = Form(None),
    generate_reels: Optional[bool] = Form(False),
    subtitles: Optional[UploadFile] = File(None),
    source_url: Optional[str] = Form(None),
    captions_lang: Optional[str] = Form(None),   # language code of `subtitles` (agent)
    captions_kind: Optional[str] = Form(None),   # "uploaded" (human) | "automatic"
    source_title: Optional[str] = Form(None),    # credit line: video title
    source_channel: Optional[str] = Form(None),  # credit line: channel / author
    source_playlist: Optional[str] = Form(None), # catalogue: playlist / course
    source_license: Optional[str] = Form(None),  # as declared on the platform
    variety: Optional[str] = Form(None),         # variety the source teaches (shi/tzm/rif/zgh/kab)
    db: Session = Depends(get_db),
):
    """One-shot capture from an ALREADY-DOWNLOADED file — download the video on
    your own computer (residential IP, so YouTube doesn't block it) and POST it
    here; Render does the rest server-side: transcribe -> correct -> translate
    -> create drills. Returns a job_id to poll via /video-analysis/job/{id}."""
    tmp_dir = None
    try:
        purge_stale_uploads()
        tmp_dir = tempfile.mkdtemp(dir=UPLOADS_TMP_ROOT)
        suffix = os.path.splitext(video.filename or "")[1] or ".mp4"
        video_path = os.path.join(tmp_dir, f"upload{suffix}")
        with open(video_path, "wb") as f:
            f.write(await video.read())

        job = VideoProcessingJobModel(
            source_url=(source_url or "").strip() or f"local-upload:{video.filename or 'video'}",
            source_filepath=video_path,
            status="PENDING",
            date_submitted=datetime.utcnow(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Captions sent by the local agent (platform subtitles, human-made when
        # available) replace ASR: exact timings, and bilingual cues keep the gloss.
        segments = []
        # Automatic captions are YouTube's own ASR with a guessed language (an
        # English lesson came back as "Arabic"); only trust them when they match
        # the language the user asked for. Human captions set the source language.
        if subtitles is not None and (captions_kind or "uploaded") == "automatic" and \
                (language or "").lower() != (captions_lang or "").lower():
            print(f"[AUTO-UPLOAD] ignoring automatic captions ({captions_lang}); language hint={language!r}")
            subtitles = None
        if subtitles is not None and not language and captions_lang:
            language = captions_lang.split("-")[0].lower()
        if subtitles is not None:
            try:
                from video_utils import parse_vtt
                raw = (await subtitles.read()).decode("utf-8", "replace")
                segments = parse_vtt(raw)
                for seg in segments:
                    db.add(VideoSegmentModel(
                        job_id=job.id,
                        segment_start_time=seg["start"],
                        segment_end_time=seg["end"],
                        text_original=cue_text_for_storage(seg),
                    ))
                db.commit()
                print(f"[AUTO-UPLOAD] {len(segments)} caption cues from {subtitles.filename}; ASR skipped")
            except Exception as e:
                print(f"[AUTO-UPLOAD] captions unusable ({e}); falling back to ASR")
                segments = []
        background_tasks.add_task(
            auto_drills_pipeline_task,
            job.id, (source_url or "").strip() or None, video_path, tmp_dir,
            language, tag, bool(apply_correction), bool(segments),
            lyrics, bool(generate_reels),
            {"title": source_title, "channel": source_channel, "playlist": source_playlist, "license": source_license,
             "variety": variety},
        )
        return {
            "job_id": job.id,
            "status": "PENDING",
            "message": "Auto pipeline started. Poll /video-analysis/job/{job_id} until drills_created appears.",
        }
    except Exception as e:
        if tmp_dir and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ---- Autonomous local capture queue ---------------------------------------
# The web app queues a URL here; a local agent (tools/capture_agent.py) running
# on the user's machine polls, downloads it on their residential IP (dodging
# YouTube's block of Render's IP), and uploads the file back — no manual step.
# Liveness of the local agent: the single-worker backend remembers the last
# poll so the web app can tell the user whether an agent is connected before
# they queue a URL that nobody will download.
_capture_agent_seen: Dict[str, Any] = {"at": None, "version": None}


# Declared before `/capture/{request_id}`: FastAPI tries routes in the order they are
# written, so with this below it the word «video» was read as a request id and answered
# 422. The same trap `/drills/similar` has to dodge.
@app.get("/capture/video")
def capture_video(url: str, db: Session = Depends(get_db)):
    """What a video gave us: its cuts in time order, and where it was left untouched.

    The capture screen could show what the machine was ABOUT to create and then never again.
    Once the drills existed there was no way back to the video they came from, even though every
    one of them carries `source_url`, `video_start_time` and `video_end_time`.

    The gaps are the point. A forty-second hole in the middle of a video means something was
    skipped; two cuts that overlap mean one of them is carrying the other's words -- which is
    exactly the fault that made drill 6854 say one thing and sound like another.
    """
    # Pel vídeo, no per la cadena: els talls d'un mateix vídeo porten cadascun el seu segon
    # dins del `source_url` (`&t=509`, `&t=521`…), i comparar-la sencera no en trobava cap.
    want = video_key(url)
    rows = [d for d in db.query(DrillModel)
            .filter(DrillModel.source_url != None, DrillModel.source_url != "")   # noqa: E711
            .order_by(sa_func.coalesce(DrillModel.video_start_time, 0).asc(),
                      DrillModel.id.asc()).all()
            if video_key(d.source_url) == want]
    if not rows:
        raise HTTPException(status_code=404, detail="D'aquest vídeo no en tenim cap frase")

    cuts = []
    for d in rows:
        cuts.append({
            "id": d.id, "start": d.video_start_time, "end": d.video_end_time,
            "text_tachelhit": d.text_tachelhit, "text_catalan": d.text_catalan,
            "text_tachelhit_suggested": d.text_tachelhit_suggested,
            "audio_url": d.audio_url, "video_url": d.video_url, "image_url": d.image_url,
            "verified": bool(d.verified), "variety": d.variety, "author": d.author,
            "tag": d.tag, "topics": d.topics,
        })

    # the holes and the overlaps, between one cut and the next
    timed = [c for c in cuts if c["start"] is not None and c["end"] is not None]
    holes, overlaps = [], []
    for a, b in zip(timed, timed[1:]):
        between = b["start"] - a["end"]
        if between >= 3.0:
            holes.append({"from": a["end"], "to": b["start"], "after": a["id"], "before": b["id"]})
        elif between < -0.25:
            overlaps.append({"by": round(-between, 2), "a": a["id"], "b": b["id"]})

    first = rows[0]
    return {
        "source_url": url,
        "title": first.source_title, "channel": first.source_channel,
        "playlist": first.source_playlist, "license": first.license,
        "cuts": cuts,
        "covered_from": timed[0]["start"] if timed else None,
        "covered_to": max((c["end"] for c in timed), default=None),
        "holes": holes, "overlaps": overlaps,
        "with_voice": sum(1 for c in cuts if c["audio_url"]),
        "verified": sum(1 for c in cuts if c["verified"]),
    }


@app.get("/capture/agent")
def capture_agent_status():
    at = _capture_agent_seen.get("at")
    online = bool(at and (datetime.utcnow() - at).total_seconds() < 45)
    return {"online": online, "last_seen": at.isoformat() + "Z" if at else None,
            "version": _capture_agent_seen.get("version")}


@app.post("/capture/request")
def capture_request(
    url: str = Body(..., embed=True),
    tag: Optional[str] = Body(None, embed=True),
    language: Optional[str] = Body(None, embed=True),
    audio_only: bool = Body(True, embed=True),
    apply_correction: bool = Body(True, embed=True),
    variety: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
):
    """Queue a URL for the local agent to download. Poll GET /capture/{id}."""
    req = CaptureRequestModel(
        url=url.strip(), tag=tag, language=language,
        audio_only=bool(audio_only), apply_correction=bool(apply_correction),
        variety=(variety or "").strip() or None,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return {"request_id": req.id, "status": "pending"}


# Un reclam que no torna. L'agent es queda la petició mentre la baixa i la puja; quan ha pujat
# diu «processing» o «done». Si no diu mai res —ha petat, s'ha quedat sense xarxa, la màquina
# s'ha adormit— la fila es quedava a «claimed» per sempre: la cua ensenyava «en curs»
# indefinidament i l'agent no la tornava a agafar mai, perquè ja no era pending.
#
# Mitja hora és molt generós per a baixar i pujar, fins i tot un vídeo llarg amb mala connexió.
STALE_CLAIM = timedelta(minutes=30)
GIVE_UP_AFTER = 3          # una URL que l'agent no pot pair no pot girar per sempre


def _requeue_abandoned_claims(db: Session) -> int:
    """Torna a la cua els reclams que ningú no ha contestat, i es rendeix al tercer.

    Es crida des d'on ja es passa —la consulta de l'agent i la de la pantalla— perquè el forat
    no demana cap tasca de fons: demana que algú se'n recordi."""
    cutoff = datetime.utcnow() - STALE_CLAIM
    stale = (db.query(CaptureRequestModel)
             .filter(CaptureRequestModel.status == "claimed",
                     CaptureRequestModel.claimed_at != None,          # noqa: E711
                     CaptureRequestModel.claimed_at < cutoff).all())
    for req in stale:
        tries = (req.attempts or 0) + 1
        req.attempts = tries
        if tries >= GIVE_UP_AFTER:
            req.status = "failed"
            req.error = (f"L'agent se la va endur {tries} vegades i no va tornar a dir res. "
                         "Mira que l'agent estigui engegat, i que aquest enllaç es pugui baixar.")
        else:
            req.status = "pending"
            req.claimed_at = None
    if stale:
        db.commit()
        print(f"[CAPTURE] {len(stale)} reclams abandonats tornats a la cua")
    return len(stale)


@app.get("/capture/pending")
def capture_pending(request: Request, db: Session = Depends(get_db)):
    """The local agent polls this: returns and CLAIMS the oldest pending
    request, or {request: null} when the queue is empty."""
    _capture_agent_seen["at"] = datetime.utcnow()
    _capture_agent_seen["version"] = request.headers.get("X-Agent-Version")
    _requeue_abandoned_claims(db)
    req = (db.query(CaptureRequestModel)
           .filter(CaptureRequestModel.status == "pending")
           .order_by(CaptureRequestModel.created_at.asc()).first())
    if not req:
        return {"request": None}
    req.status = "claimed"
    req.claimed_at = datetime.utcnow()
    req.attempts = (req.attempts or 0)
    db.commit()
    db.refresh(req)
    return {"request": {
        "id": req.id, "url": req.url, "tag": req.tag, "language": req.language,
        "audio_only": req.audio_only, "apply_correction": req.apply_correction,
        "variety": req.variety,
    }}


@app.post("/capture/{request_id}/done")
def capture_done(request_id: int, job_id: Optional[int] = Body(None, embed=True),
                 drills_created: Optional[int] = Body(None, embed=True), db: Session = Depends(get_db)):
    """Agent reports it uploaded the file; links the resulting pipeline job. When the agent
    processed the request on ANOTHER backend (--process-at, agent 2.6) it sends drills_created
    instead: the job id belongs to that backend's DB, so it is not stored here and the request
    is done."""
    req = db.query(CaptureRequestModel).filter(CaptureRequestModel.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Capture request not found")
    if drills_created is not None:
        req.status = "done"
        req.job_id = None
        req.drills_created = int(drills_created)
    else:
        req.status = "processing"
        req.job_id = job_id
    db.commit()
    return {"ok": True}


@app.post("/capture/{request_id}/fail")
def capture_fail(request_id: int, error: str = Body("", embed=True), db: Session = Depends(get_db)):
    req = db.query(CaptureRequestModel).filter(CaptureRequestModel.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Capture request not found")
    req.status = "failed"
    req.error = (error or "")[:500]
    db.commit()
    return {"ok": True}


def _drills_created_count(value) -> Optional[int]:
    """A job's processing_log keeps the LIST of drill ids; the queue and status endpoints
    report a COUNT (the agent-processed rows store an int). The web app once printed the
    whole id list in one line and pushed the phone layout sideways."""
    if value is None:
        return None
    if isinstance(value, (list, tuple, set)):
        return len(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


_agent_latest_cache: Dict[str, Any] = {}


def _published_agent_version() -> Optional[str]:
    """The version the release is built from: tools/capture_agent.py's own `__version__`.

    An old agent fails in ways that look like a broken video, so it is worth saying out loud when
    the one connected is behind. Read once; a deploy is what changes it.
    """
    if "v" in _agent_latest_cache:
        return _agent_latest_cache["v"]
    found = None
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (os.path.join(here, "..", "tools", "capture_agent.py"),
                 os.path.join(here, "tools", "capture_agent.py")):
        try:
            with open(os.path.normpath(path), encoding="utf-8") as f:
                for line in f:
                    if line.startswith("__version__"):
                        found = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except OSError:
            continue
        if found:
            break
    _agent_latest_cache["v"] = found
    return found


@app.post("/capture/{request_id}/retry")
def capture_retry(request_id: int, db: Session = Depends(get_db),
                  user: UserModel = Depends(require_user)):
    """Put a request back in the queue. A capture fails for reasons that pass: the video was
    private for an hour, the agent was an old one, the network went. Retrying is the obvious
    thing, and until now the only way was to paste the URL again."""
    req = db.query(CaptureRequestModel).filter(CaptureRequestModel.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Aquesta captura no existeix")
    req.status = "pending"
    req.error = None
    req.claimed_at = None
    db.commit()
    return {"id": req.id, "status": req.status}


@app.delete("/capture/{request_id}")
def capture_forget(request_id: int, db: Session = Depends(get_db),
                   user: UserModel = Depends(require_user)):
    """Take a finished or failed request out of the list. What is still being worked on stays:
    forgetting a running job would leave the agent working on something nobody is waiting for."""
    req = db.query(CaptureRequestModel).filter(CaptureRequestModel.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Aquesta captura no existeix")
    if req.status in ("claimed", "processing"):
        raise HTTPException(status_code=409, detail="Aquesta encara s\u2019est\u00e0 fent; espera que acabi")
    db.delete(req)
    db.commit()
    return {"id": request_id, "forgotten": True}


@app.get("/capture/queue")
def capture_queue(limit: int = 40, db: Session = Depends(get_db)):
    """The last `limit` capture requests, newest first, with state, drill count and error:
    what the agent is doing, for the Captura tab.

    It also returns abandoned claims to the queue before answering. That is not housekeeping
    out of place: when the agent dies holding a request, NOBODY polls /capture/pending any more,
    so the only thing that can notice is the screen somebody opens to ask why it is stuck.
    """
    _requeue_abandoned_claims(db)
    rows = (db.query(CaptureRequestModel).order_by(CaptureRequestModel.created_at.desc())
            .limit(max(1, min(limit, 200))).all())
    out = []
    for r in rows:
        drills_created = getattr(r, "drills_created", None)
        job_status = None
        if r.job_id and drills_created is None:
            job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == r.job_id).first()
            if job:
                job_status = job.status
                if job.processing_log:
                    try:
                        drills_created = _drills_created_count(json.loads(job.processing_log).get("drills_created"))
                    except (ValueError, TypeError):
                        pass
        out.append({"id": r.id, "url": r.url, "tag": r.tag, "variety": r.variety, "status": r.status,
                    "job_status": job_status, "drills_created": drills_created, "error": r.error,
                    "created_at": iso_z(r.created_at) if r.created_at else None,
                    "claimed_at": iso_z(r.claimed_at) if r.claimed_at else None})
    agent_at = _capture_agent_seen.get("at")
    return {"requests": out,
            "agent": {"online": bool(agent_at and (datetime.utcnow() - agent_at).total_seconds() < 45),
                      "version": _capture_agent_seen.get("version"),
                      "latest": _published_agent_version()}}


@app.get("/capture/{request_id}")
def capture_status(request_id: int, db: Session = Depends(get_db)):
    """Web-app polling: request status + drills_created once processing finishes."""
    req = db.query(CaptureRequestModel).filter(CaptureRequestModel.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Capture request not found")
    drills_created = getattr(req, "drills_created", None)
    job_status = None
    if req.job_id:
        job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == req.job_id).first()
        if job:
            job_status = job.status
            if job.processing_log:
                try:
                    drills_created = _drills_created_count(json.loads(job.processing_log).get("drills_created"))
                except (ValueError, TypeError):
                    pass
            if job.status == "COMPLETED" and req.status != "done":
                req.status = "done"
                db.commit()
    return {
        "id": req.id, "status": req.status, "url": req.url,
        "job_id": req.job_id, "job_status": job_status,
        "drills_created": drills_created, "error": req.error,
    }


@app.post("/video-analysis/correct")
async def correct_video_segments(
    segments: List[Dict] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Run each segment's text through the correction layer: glossary
    sound->spelling fixes, then mapping onto the user's curated phrase dataset
    (DeepSeek when configured, local fuzzy matching otherwise). Opt-in — the
    review table stays the human checkpoint.
    """
    try:
        drills = db.query(DrillModel).filter(DrillModel.is_correction_dataset == True).all()
        if not drills:
            drills = db.query(DrillModel).filter(
                DrillModel.text_tachelhit != None,
                DrillModel.text_tachelhit != ''
            ).limit(100).all()
        phrases = [d.text_tachelhit for d in drills if d.text_tachelhit]
        glossary = db.query(GlossaryItemModel).all()
        svc = get_correction_service()

        for seg in segments:
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            fixed = apply_glossary(text, [(g.word_sound, g.correct_spelling) for g in glossary])
            try:
                corrected, score = await asyncio.to_thread(svc.correct_transcription, fixed, phrases)
                seg["text"] = corrected
                seg["correction_score"] = score
            except Exception as e:
                print(f"[API] Correction error for segment: {e}")
                seg["text"] = fixed

        return segments
    except Exception as e:
        print(f"[API] Error in correct_video_segments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/video-analysis/ocr")
def ocr_video_segments(
    video_path: str = Body(...),
    segments: List[Dict] = Body(...),
    band_ratio: float = Body(0.28)
):
    """
    Read burned-in subtitles off a captured video: samples one frame per
    segment (midpoint), crops the bottom subtitle band, and sends it to the
    OCR Space (EasyOCR: Latin + Arabic). Results land in seg["text_ocr"] for
    mandatory human review — nothing is written to drills directly.
    See docs/OCR_FEATURE_SCOPE.md.
    """
    if not is_managed_upload_path(video_path):
        raise HTTPException(status_code=400, detail="video_path is not a managed upload")
    if not os.path.exists(video_path):
        raise HTTPException(status_code=400, detail="Video file no longer available; re-import the URL")

    ocr_space_url = os.getenv("HUGGINGFACE_OCR_SPACE_URL")
    if not ocr_space_url:
        raise HTTPException(status_code=500, detail="HUGGINGFACE_OCR_SPACE_URL not configured")
    ocr_endpoint = resolve_hf_space_host(ocr_space_url) + "/ocr"

    hf_token = os.getenv("HUGGINGFACE_API_KEY")
    headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}

    from moviepy.video.io.VideoFileClip import VideoFileClip
    from PIL import Image

    band_ratio = min(max(band_ratio, 0.1), 0.6)
    clip = VideoFileClip(video_path)
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            for i, seg in enumerate(segments):
                try:
                    midpoint = (float(seg["start"]) + float(seg["end"])) / 2
                    t = min(max(midpoint, 0), max(clip.duration - 0.05, 0))
                    frame_path = os.path.join(tmp_dir, f"frame_{i}.jpg")
                    clip.save_frame(frame_path, t=t)

                    # Crop the bottom band where burned-in subtitles live
                    img = Image.open(frame_path)
                    w, h = img.size
                    band = img.crop((0, int(h * (1 - band_ratio)), w, h))
                    band_path = os.path.join(tmp_dir, f"band_{i}.jpg")
                    band.save(band_path, "JPEG", quality=90)

                    with open(band_path, "rb") as f:
                        resp = requests.post(
                            ocr_endpoint,
                            files={"image": (f"band_{i}.jpg", f, "image/jpeg")},
                            headers=headers,
                            timeout=120
                        )
                    resp.raise_for_status()
                    results = resp.json().get("results", [])
                    texts = [r["text"] for r in results if r.get("confidence", 0) >= 0.35]
                    seg["text_ocr"] = " ".join(texts).strip()
                except Exception as seg_err:
                    print(f"[OCR] Segment {i} failed: {seg_err}")
                    seg["text_ocr"] = seg.get("text_ocr", "")
    finally:
        clip.close()

    return segments

def _attach_lesson_lines(segments: List[Dict], lines: List[Dict]) -> List[Dict]:
    """Lay lesson items (text/tifinagh/latin/gloss, no times) on ASR segments (times, a
    rough Latin guess): same positional + fuzzy matching as the lyrics alignment, on the
    Latin reading. Each matched segment takes the item's text and gloss; items that no
    segment claims are kept untimed (a text drill with a synthetic voice)."""
    import difflib
    if not lines or not segments:
        return segments
    n_seg, n_lines = len(segments), len(lines)
    used = set()
    for i, seg in enumerate(segments):
        expected = round(i * (n_lines - 1) / max(1, n_seg - 1)) if n_seg > 1 else 0
        window = range(max(0, expected - 2), min(n_lines, expected + 3))
        asr_text = (seg.get("text") or "").lower()
        best_idx, best_score = expected, -1.0
        for j in window:
            cand = (lines[j].get("latin") or lines[j].get("text") or "").lower()
            score = difflib.SequenceMatcher(None, asr_text, cand).ratio() - (0.15 if j in used else 0.0)
            if score > best_score:
                best_idx, best_score = j, score
        used.add(best_idx)
        item = lines[best_idx]
        seg["text_asr"] = seg.get("text")
        seg["text"] = item.get("tifinagh") or item.get("text") or seg.get("text")
        for k in ("latin", "tifinagh", "gloss", "gloss_lang", "kind"):
            if item.get(k):
                seg[k] = item[k]
    leftovers = [dict(lines[j]) for j in range(n_lines) if j not in used]
    for it in leftovers:
        it["start"], it["end"] = None, None
    return segments + leftovers


def dedupe_repeated_lines(segments: List[Dict]) -> List[Dict]:
    """One drill per distinct Tamazight line: when the same line (same transliteration key)
    appears again later — a chorus, a repeated verse — the later copies are dropped and the
    first keeps its clip. Lines without text are untouched. Pure."""
    from transliteration import to_forms
    seen = set()
    out = []
    dropped = 0
    for seg in segments:
        text = (seg.get("text_tachelhit") or seg.get("text") or "").strip()
        key = to_forms(text)["key"] if text else ""
        if key and key in seen:
            dropped += 1
            continue
        if key:
            seen.add(key)
        out.append(seg)
    if dropped:
        print(f"[AUTO] {dropped} repeated line(s) dropped (chorus): one drill per distinct line")
    return out


def _align_known_lines(media_path: str, lines: List[str]) -> Optional[List[Dict]]:
    """Time KNOWN lines (lyrics, lesson lines, subtitles) with the ASR Space's /align
    (NeMo forced alignment): one segment per line, in order, with word times. Returns
    None when the Space has no /align yet, fails, or answers a different number of
    lines — the caller then falls back to transcribe-and-fuzzy-match."""
    lines = [(l or "").strip() for l in lines]
    if os.getenv("ALIGN_KNOWN_TEXT", "1") != "1" or not any(lines) or not media_path:
        return None
    space = os.getenv("HUGGINGFACE_ASR_SPACE_URL", ASR_SPACE_DEFAULT)
    url = resolve_hf_space_host(space) + "/align"
    hf_token = os.getenv("HUGGINGFACE_API_KEY")
    headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
    try:
        with open(media_path, "rb") as f:
            resp = requests.post(url, files={"audio_file": (os.path.basename(media_path), f, "application/octet-stream")},
                                 data={"text": "\n".join(l for l in lines if l), "split_on_newline": "true"},
                                 headers=headers, timeout=900)
        if resp.status_code != 200:
            print(f"[ALIGN] /align answered {resp.status_code}: {resp.text[:160]}")
            return None
        segs = resp.json().get("segments") or []
    except Exception as e:
        print(f"[ALIGN] /align failed: {e}")
        return None
    kept = [l for l in lines if l]
    if len(segs) != len(kept):
        print(f"[ALIGN] {len(kept)} lines but {len(segs)} aligned segments; falling back")
        return None
    out = []
    for line, sg in zip(kept, segs):
        try:
            start, end = float(sg.get("start")), float(sg.get("end"))
        except (TypeError, ValueError):
            return None
        if end <= start:
            end = start + 0.5
        out.append({"start": round(start, 2), "end": round(end, 2), "text": line, "words": sg.get("words") or []})
    short = sum(1 for o in out if o["end"] - o["start"] < 0.25)
    if short:
        print(f"[ALIGN] {short}/{len(out)} lines shorter than 0.25 s (check the text matches the audio)")
    return out


def _align_lyrics_lines(segments: List[Dict], lyrics: str) -> List[Dict]:
    """
    Swap ASR-guessed segment text for real lyric lines while keeping the ASR
    timestamps (ASR hears sung vocals poorly but times them well). Each
    segment gets the best fuzzy-matching lyric line near its proportionally
    expected position; the original ASR guess is preserved in text_asr.
    """
    import difflib

    raw = [l.strip() for l in (lyrics or "").splitlines() if l.strip()]
    if not raw or not segments:
        return segments
    # "line | meaning": the meaning (Catalan) rides along as a gloss so the pipeline
    # translates the gloss, never the Tamazight line (NLLB invents sentences for a
    # machine-heard line). "line" alone keeps the old behaviour.
    lines, glosses = [], []
    for l in raw:
        if " | " in l:
            a, b = l.split(" | ", 1)
            lines.append(a.strip()); glosses.append(b.strip() or None)
        else:
            lines.append(l); glosses.append(None)

    n_seg, n_lines = len(segments), len(lines)
    used = set()
    for i, seg in enumerate(segments):
        expected = round(i * (n_lines - 1) / max(1, n_seg - 1)) if n_seg > 1 else 0
        window = range(max(0, expected - 2), min(n_lines, expected + 3))
        asr_text = (seg.get("text") or "").lower()
        best_idx, best_score = expected, -1.0
        for j in window:
            score = difflib.SequenceMatcher(None, asr_text, lines[j].lower()).ratio()
            if j in used:  # prefer lines not already claimed
                score -= 0.15
            if score > best_score:
                best_idx, best_score = j, score
        used.add(best_idx)
        seg["text_asr"] = seg.get("text")
        seg["text"] = lines[best_idx]
        if glosses[best_idx]:
            seg["gloss"] = glosses[best_idx]
            seg["gloss_lang"] = "ca"
    return segments

@app.post("/video-analysis/align-lyrics")
def align_lyrics_to_segments(
    segments: List[Dict] = Body(...),
    lyrics: str = Body(...)
):
    """Manual alignment endpoint for the review table. See _align_lyrics_lines."""
    if not (lyrics or "").strip():
        raise HTTPException(status_code=400, detail="No lyric lines provided")
    return _align_lyrics_lines(segments, lyrics)

# Which segment field each translation target fills; these are the three
# text fields a Drill actually stores.
TRANSLATE_TARGET_FIELDS = {
    "ca": "text_catalan",
    "ar": "text_arabic",
    "shi": "text_tachelhit",
}

@app.post("/video-analysis/translate")
async def translate_video_segments(
    segments: List[Dict] = Body(...),
    source_lang: str = Body("auto"),
    target_langs: Optional[List[str]] = Body(None),
    draft_tachelhit: Optional[bool] = Body(False)
):
    """
    Translate a list of video segments using the fine-tuned NLLB Hugging Face
    Space (Google Translate has no Tachelhit/Tamazight support). By default
    translates to Catalan; pass target_langs (subset of ca/ar/shi) to fill
    several drill languages in one call. Targets equal to the source language
    are skipped.

    draft_tachelhit=True (foreign-language source, e.g. an English video):
    the machine Tachelhit goes to text_tachelhit_suggested (a DRAFT), never the
    gold text_tachelhit — because MT into this low-resource variety is only a
    starting point a human must correct.
    """
    try:
        # Map the caller's language code to the friendly name translate_with_hf
        # expects. ASR output (and unknown/"auto") is treated as Tachelhit, the
        # primary language of this app's source videos.
        effective_source = source_lang if source_lang not in (None, "", "auto") else "shi"
        src_name = LANGUAGE_CODE_MAP.get(effective_source, effective_source)

        targets = [t for t in (target_langs or ["ca"]) if t in TRANSLATE_TARGET_FIELDS]
        if not targets:
            targets = ["ca"]

        translated_segments = []
        for seg in segments:
            original_text = (seg.get("text") or "").strip()
            if original_text:
                for tgt in targets:
                    # Same language as the source: the original text already is it
                    if LANGUAGE_CODE_MAP.get(tgt) == src_name:
                        continue
                    # Foreign source: route machine Tachelhit to the draft column
                    field = ("text_tachelhit_suggested" if (draft_tachelhit and tgt == "shi")
                             else TRANSLATE_TARGET_FIELDS[tgt])
                    try:
                        seg[field] = await asyncio.to_thread(
                            translate_with_hf, original_text, src_name, LANGUAGE_CODE_MAP[tgt]
                        )
                    except Exception as e:
                        print(f"[API] Translation error ({tgt}) for segment: {e}")
                        # Preserve any existing value rather than blanking it out
                        seg[field] = seg.get(field, "")
            translated_segments.append(seg)

        return translated_segments
    except Exception as e:
        print(f"[API] Error in translate_video_segments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/video-analysis/create-drills")
async def create_drills_from_video(
    url: Optional[str] = Body(None),
    video_path: Optional[str] = Body(None),
    segments: List[Dict] = Body(...),
    source_lang: Optional[str] = Body(None),
    tag: Optional[str] = Body(None),
    cookies: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Take selected segments, clip them, and create drills. Works with URL or Local Path.
    """
    # Only accept paths pointing at files this API created via
    # /video-analysis/upload — never arbitrary server files
    if video_path and not is_managed_upload_path(video_path):
        raise HTTPException(status_code=400, detail="video_path is not a managed upload")

    try:
        job = VideoProcessingJobModel(
            source_url=url or video_path,
            status="IN_PROGRESS",
            date_submitted=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        drills_created = []

        if video_path and os.path.exists(video_path):
            # Path A: Local file upload
            for seg in segments:
                original_text = seg.get("text")
                # Prefer explicit per-language translations from the review
                # table; otherwise route the original text by source language
                drill_tachelhit = seg.get("text_tachelhit") or (original_text if source_lang in [None, 'shi', 'ber'] else None)
                drill_arabic = seg.get("text_arabic") or (original_text if source_lang == 'ar' else None)
                _junk = looks_like_junk_asr(drill_tachelhit, attested=source_lang in [None, 'shi', 'ber'])
                if _junk:
                    print(f"[CreateDrills] skipping junk segment ({_junk}): {str(drill_tachelhit)[:60]!r}")
                    continue

                db_drill = DrillModel(
                    text_catalan=seg.get("text_catalan"),
                    text_tachelhit=drill_tachelhit,
                    text_arabic=drill_arabic,
                    text_tachelhit_suggested=seg.get("text_tachelhit_suggested"),
                    text_catalan_suggested=seg.get("text_catalan_suggested"),
                    tag=tag or "file_import",
                    author="Manual Upload",
                    source_url=url
                )
                db.add(db_drill)
                db.commit()
                db.refresh(db_drill)

                try:
                    if is_audio_file(video_path):
                        # Audio source (podcast / voice note): the clip becomes
                        # the drill's Tachelhit audio, no video/thumbnail
                        res = process_and_upload_audio_segment(video_path, seg["start"], seg["end"], db_drill.id)
                        db_drill.audio_url = normalize_media_url(res["audio_url"])
                    else:
                        res = process_and_upload_segment(video_path, seg["start"], seg["end"], db_drill.id)
                        db_drill.video_url = normalize_media_url(res["video_url"])
                        db_drill.image_url = normalize_media_url(res["image_url"])
                    try:
                        tts_url = generate_catalan_tts(seg.get("text_catalan"), db_drill.id)
                        db_drill.audio_tts_url = tts_url
                    except: pass
                    db.commit()
                    drills_created.append(db_drill.id)
                except Exception as e:
                    print(f"Error processing segment: {e}")
                    db.rollback()

        elif url:
            # Path B: YouTube URL - OFF-LOADED TO HF SPACE
            print(f"[API] Offloading YouTube clipping to HF Space: {url}")
            for seg in segments:
                original_text = seg.get("text")
                # Prefer explicit per-language translations when present
                drill_tachelhit = seg.get("text_tachelhit") or (original_text if source_lang in [None, 'shi', 'ber'] else None)
                drill_arabic = seg.get("text_arabic") or (original_text if source_lang == 'ar' else None)
                _junk = looks_like_junk_asr(drill_tachelhit, attested=source_lang in [None, 'shi', 'ber'])
                if _junk:
                    print(f"[CreateDrills] skipping junk segment ({_junk}): {str(drill_tachelhit)[:60]!r}")
                    continue

                db_drill = DrillModel(
                    text_catalan=seg.get("text_catalan"),
                    text_tachelhit=drill_tachelhit,
                    text_arabic=drill_arabic,
                    text_tachelhit_suggested=seg.get("text_tachelhit_suggested"),
                    text_catalan_suggested=seg.get("text_catalan_suggested"),
                    tag=tag or "video_capture",
                    source_url=url
                )
                db.add(db_drill)
                db.commit()
                db.refresh(db_drill)

                try:
                    # OFF-LOADED CALL
                    res = remote_process_and_upload_segment(url, seg["start"], seg["end"], db_drill.id)
                    db_drill.video_url = normalize_media_url(res["video_url"])
                    db_drill.image_url = normalize_media_url(res["image_url"])
                    try:
                        tts_url = generate_catalan_tts(seg.get("text_catalan"), db_drill.id)
                        db_drill.audio_tts_url = tts_url
                    except: pass
                    db.commit()
                    drills_created.append(db_drill.id)
                except Exception as e:
                    print(f"Error processing segment: {e}")
                    db.rollback()

        job.status = "COMPLETED"
        db.commit()
        return {"status": "success", "drills_created": drills_created}

    except Exception as e:
        print(f"[API] Error in create_drills_from_video: {e}")
        if 'job' in locals():
            job.status = "FAILED"
            job.error_message = str(e)
            db.commit()
        raise HTTPException(status_code=500, detail=str(e))

# ===================== USERS (multi-tenancy, auditor Phase 1) =====================
# (get_current_user lives next to get_db near the top of the file)

# Naive in-memory rate limit for registration (per process; resets on deploy)
_register_attempts: Dict[str, List[float]] = {}

# Canonical variety vocabulary (ISO 639-3). Kept small + honest: the speaker's
# variety stays distinct and is never silently defaulted to the standard (zgh).
VARIETIES = [
    {"code": "shi", "label": "Taixelhit (Tashelhit)"},
    {"code": "tzm", "label": "Tamazight de l'Atles Central"},
    {"code": "tdl", "label": "Taixelhit de transició (Tadla–Azilal: Beni Mellal, Azilal, Demnate)"},
    {"code": "rif", "label": "Tarifit (Rif)"},
    {"code": "zgh", "label": "Amazic estàndard marroquí (IRCAM)"},
    {"code": "kab", "label": "Cabilenc (Kabyle)"},
    {"code": "other", "label": "Altra / no ho sé"},
]
_VARIETY_CODES = {v["code"] for v in VARIETIES}


@app.get("/varieties")
def list_varieties():
    """The controlled variety vocabulary (code + Catalan label)."""
    return VARIETIES


@app.post("/users/register")
def register_user(
    request: Request,
    username: str = Body(..., embed=True),
    display_name: Optional[str] = Body(None, embed=True),
    variety: Optional[str] = Body(None, embed=True),
    region: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db)
):
    """
    Create a contributor/learner identity. Returns a personal token the client
    must send as the X-User-Token header on every request; it is shown once
    and stored only as a hash.
    """
    ip = request.client.host if request.client else "unknown"
    now_ts = datetime.utcnow().timestamp()
    attempts = [t for t in _register_attempts.get(ip, []) if now_ts - t < 3600]
    if len(attempts) >= 5:
        raise HTTPException(status_code=429, detail="Too many registrations from this address; try again later")
    attempts.append(now_ts)
    _register_attempts[ip] = attempts

    uname = (username or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_\-\.]{3,32}", uname):
        raise HTTPException(status_code=400, detail="Username must be 3-32 chars: a-z 0-9 _ - .")
    if db.query(UserModel).filter(UserModel.username == uname).first():
        raise HTTPException(status_code=409, detail="Username already taken")

    raw_token = secrets.token_hex(16)
    user = UserModel(
        username=uname,
        display_name=(display_name or uname).strip(),
        token=_hash_token(raw_token),
        variety=(variety or None),
        region=(region or "").strip() or None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"username": user.username, "display_name": user.display_name,
            "variety": user.variety, "region": user.region, "token": raw_token}

@app.post("/auth/signup")
def auth_signup(request: Request, email: str = Body(..., embed=True), password: str = Body(..., embed=True),
                username: str = Body(..., embed=True), display_name: Optional[str] = Body(None, embed=True),
                variety: Optional[str] = Body(None, embed=True), region: Optional[str] = Body(None, embed=True),
                device: Optional[str] = Body(None, embed=True), db: Session = Depends(get_db)):
    """Create an account (e-mail + password + username). Returns a session token for this
    device (X-User-Token) and the profile. Admins are the ADMIN_EMAILS env list."""
    ip = request.client.host if request.client else "unknown"
    _rate_limit(_register_attempts, ip, 5, 3600)
    email_n = (email or "").strip().lower()
    if not _valid_email(email_n):
        raise HTTPException(status_code=400, detail="Adreça de correu no vàlida")
    _check_password_strength(password)
    uname = (username or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_\-\.]{3,32}", uname):
        raise HTTPException(status_code=400, detail="Username must be 3-32 chars: a-z 0-9 _ - .")
    if db.query(UserModel).filter(UserModel.email == email_n).first():
        raise HTTPException(status_code=409, detail="Ja hi ha un compte amb aquest correu")
    if db.query(UserModel).filter(UserModel.username == uname).first():
        raise HTTPException(status_code=409, detail="Username already taken")
    user = UserModel(username=uname, display_name=(display_name or uname).strip(), token=_hash_token(secrets.token_hex(16)),
                     email=email_n, password_hash=_hash_password(password),
                     is_admin=(email_n in _admin_emails() or _no_admin_yet(db)),
                     variety=(variety or None), region=(region or "").strip() or None)
    if user.is_admin and email_n not in _admin_emails():
        print(f"[AUTH] {email_n} is the first account of this library: granted administrator")
    db.add(user); db.commit(); db.refresh(user)
    return {**_user_payload(user), "token": _new_session(db, user, device)}


@app.post("/auth/login")
def auth_login(request: Request, login: str = Body(..., embed=True), password: str = Body(..., embed=True),
               device: Optional[str] = Body(None, embed=True), db: Session = Depends(get_db)):
    """Sign in with e-mail (or username) + password; returns a new session token for this device."""
    ip = request.client.host if request.client else "unknown"
    _rate_limit(_login_attempts, ip, 10, 900)
    key = (login or "").strip().lower()
    user = db.query(UserModel).filter((UserModel.email == key) | (UserModel.username == key)).first()
    if user is None or not _verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Correu o contrasenya incorrectes")
    if user.email and user.email in _admin_emails() and not user.is_admin:
        user.is_admin = True; db.commit()
    return {**_user_payload(user), "token": _new_session(db, user, device)}


@app.post("/auth/logout")
def auth_logout(request: Request, db: Session = Depends(get_db)):
    """Forget this device's session (the legacy registration token is not affected)."""
    token = (request.headers.get("x-user-token") or "").strip()
    if token:
        db.query(UserSessionModel).filter(UserSessionModel.token_hash == _hash_token(token)).delete()
        db.commit()
    return {"ok": True}


@app.post("/auth/attach")
def auth_attach(email: str = Body(..., embed=True), password: str = Body(..., embed=True),
                user: UserModel = Depends(require_user), db: Session = Depends(get_db)):
    """A token identity (registered before accounts existed) adds an e-mail and a password."""
    email_n = (email or "").strip().lower()
    if not _valid_email(email_n):
        raise HTTPException(status_code=400, detail="Adreça de correu no vàlida")
    _check_password_strength(password)
    other = db.query(UserModel).filter(UserModel.email == email_n, UserModel.id != user.id).first()
    if other:
        raise HTTPException(status_code=409, detail="Ja hi ha un compte amb aquest correu")
    user.email = email_n; user.password_hash = _hash_password(password); user.is_admin = user.is_admin or email_n in _admin_emails()
    db.commit()
    return _user_payload(user)


@app.post("/auth/username")
def auth_change_username(username: str = Body(..., embed=True),
                         user: UserModel = Depends(require_user), db: Session = Depends(get_db)):
    """Change the handle people see («@pablo»). Everything a person has given the library hangs on
    the account, not on the name, so nothing is lost by changing it."""
    uname = (username or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_\-\.]{3,32}", uname):
        raise HTTPException(status_code=400, detail="El nom d'usuari té de 3 a 32 caràcters: a-z 0-9 _ - .")
    if uname == (user.username or "").lower():
        return _user_payload(user)
    if db.query(UserModel).filter(UserModel.username == uname, UserModel.id != user.id).first():
        raise HTTPException(status_code=409, detail="Aquest nom d'usuari ja és d'algú altre")
    was = user.username
    user.username = uname
    if not (user.display_name or "").strip() or (user.display_name or "").strip().lower() == (was or "").lower():
        user.display_name = uname  # the name shown followed the handle: keep them together
    db.commit()
    print(f"[AUTH] @{was} is now @{uname}")
    return _user_payload(user)


@app.post("/auth/password")
def auth_change_password(old_password: str = Body(..., embed=True), new_password: str = Body(..., embed=True),
                         user: UserModel = Depends(require_user), db: Session = Depends(get_db)):
    if user.password_hash and not _verify_password(old_password, user.password_hash):
        raise HTTPException(status_code=401, detail="La contrasenya actual no és correcta")
    _check_password_strength(new_password)
    user.password_hash = _hash_password(new_password)
    db.commit()
    return {"ok": True}


@app.post("/auth/forgot")
def auth_forgot(request: Request, email: Optional[str] = Body(None, embed=True),
                login: Optional[str] = Body(None, embed=True), db: Session = Depends(get_db)):
    """E-mail a 6-digit reset code (30 min) to the account's address. Say who you are with your
    e-mail OR your user name: someone who signed up without an address has only the name, and that
    is exactly the person who cannot ask for help any other way. Always answers ok, so neither
    addresses nor names can be probed from outside."""
    ip = request.client.host if request.client else "unknown"
    _rate_limit(_login_attempts, ip, 10, 900)
    if not _mail_ready():
        # Not an error: this library recovers accounts with a code an admin hands over. The page
        # says so instead of showing a server fault nobody can act on.
        return {"ok": True, "mail": False}
    key = (login or email or "").strip().lower()
    user = db.query(UserModel).filter((UserModel.email == key) | (UserModel.username == key)).first() if key else None
    if user and user.email:  # with no address there is nowhere to send it: ask the admin for a code
        code = f"{secrets.randbelow(10**6):06d}"
        user.reset_code_hash = _hash_token(code); user.reset_expires = datetime.utcnow() + timedelta(minutes=30)
        db.commit()
        try:
            _send_email(user.email, "Tamazight Drills: codi per restablir la contrasenya",
                        f"Hola {user.display_name or user.username},\n\nEl teu codi és: {code}\nCaduca en 30 minuts.\n")
        except Exception as e:
            print(f"[AUTH] reset e-mail failed: {e}")
    return {"ok": True}


@app.get("/admin/users")
def admin_users(q: Optional[str] = None, limit: int = 200,
                _admin: UserModel = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin: who is in this library. Newest first, with what each person has given it."""
    rows = db.query(UserModel).order_by(UserModel.id.desc()).limit(max(1, min(limit, 500))).all()
    if q:
        needle = q.strip().lower()
        rows = [u for u in rows if needle in (u.username or "").lower()
                or needle in (u.display_name or "").lower() or needle in (u.email or "").lower()]
    made = dict(db.query(DrillModel.created_by_user_id, sa_func.count(DrillModel.id))
                .filter(DrillModel.created_by_user_id.isnot(None))
                .group_by(DrillModel.created_by_user_id).all())
    takes = dict(db.query(RecordingModel.user_id, sa_func.count(RecordingModel.id))
                 .filter(RecordingModel.user_id.isnot(None))
                 .group_by(RecordingModel.user_id).all())
    return {"users": [{"id": u.id, "username": u.username, "display_name": u.display_name,
                       "email": u.email, "is_admin": bool(u.is_admin), "is_native": u.is_native,
                       "variety": u.variety, "region": u.region,
                       "drills": made.get(u.id, 0), "takes": takes.get(u.id, 0),
                       "date_created": iso_z(u.date_created)} for u in rows]}


@app.post("/admin/users/{user_id}/admin")
def admin_set_admin(user_id: int, is_admin: bool = Body(..., embed=True),
                    me: UserModel = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin: make somebody an administrator, or stop them being one. Two guards keep a library
    from locking itself out: you cannot demote yourself, and the last administrator stays."""
    person = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="No hi ha ningú amb aquest identificador")
    if person.id == me.id and not is_admin:
        raise HTTPException(status_code=400, detail="No et pots treure a tu mateix: que ho faci un altre administrador")
    if not is_admin and db.query(UserModel).filter(UserModel.is_admin.is_(True)).count() <= 1:
        raise HTTPException(status_code=400, detail="És l'únic administrador que queda")
    person.is_admin = bool(is_admin)
    db.commit()
    print(f"[AUTH] @{me.username} {'made' if is_admin else 'unmade'} @{person.username} an administrator")
    return {"id": person.id, "username": person.username, "is_admin": bool(person.is_admin)}


@app.get("/admin/mail")
def admin_mail_get(_admin: UserModel = Depends(require_admin), db: Session = Depends(get_db)):
    """The mail sender as the app has it: the password is never returned, only whether one is set."""
    saved = {r.key: (r.value or "") for r in db.query(AppSettingModel).filter(AppSettingModel.key.in_(MAIL_KEYS)).all()}
    out = {k: (saved.get(k) or os.getenv(k) or "") for k in MAIL_KEYS if k != "SMTP_PASS"}
    out["has_password"] = bool((saved.get("SMTP_PASS") or os.getenv("SMTP_PASS") or "").strip())
    out["from_app"] = {k: bool((saved.get(k) or "").strip()) for k in MAIL_KEYS}
    out["ready"] = bool((mail_setting("MAIL_API_PROVIDER") and mail_setting("MAIL_API_KEY") and (mail_setting("SMTP_FROM") or mail_setting("SMTP_USER")))
                        or (mail_setting("SMTP_HOST") and mail_setting("SMTP_USER") and mail_setting("SMTP_PASS")))
    out["MAIL_API_PROVIDER"] = mail_setting("MAIL_API_PROVIDER")
    out["has_api_key"] = bool(mail_setting("MAIL_API_KEY"))
    return out


@app.post("/admin/mail")
def admin_mail_set(settings: Dict[str, str] = Body(..., embed=True), _admin: UserModel = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin: save the mail sender (SMTP_HOST/PORT/USER/PASS/FROM) from the app. An empty value
    leaves that setting as it is; «-» clears it."""
    for k, v in (settings or {}).items():
        if k not in MAIL_KEYS:
            continue
        v = (v or "").strip()
        if not v:
            continue
        row = db.query(AppSettingModel).filter(AppSettingModel.key == k).first()
        val = "" if v == "-" else v
        if row:
            row.value = val; row.updated_at = datetime.utcnow()
        else:
            db.add(AppSettingModel(key=k, value=val))
    db.commit()
    return admin_mail_get(_admin=_admin, db=db)


@app.post("/admin/mail/test")
def admin_mail_test(to: Optional[str] = Body(None, embed=True), _admin: UserModel = Depends(require_admin)):
    """Admin: send a test message to check the sender works."""
    dest = (to or _admin.email or "").strip()
    if not dest:
        raise HTTPException(status_code=400, detail="Digues a quina adreça l'envio")
    if not _mail_ready():
        raise HTTPException(status_code=503, detail="Encara falten dades del servidor de correu")
    try:
        ok = _send_email(dest, "Tamazight Drills: prova d'enviament",
                         "Això és una prova. Si l'has rebut, el restabliment de contrasenya ja funciona.\n")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"El servidor de correu ha fallat: {str(e)[:200]}")
    if not ok:
        raise HTTPException(status_code=502, detail="El servidor de correu no ha acceptat el missatge")
    return {"sent_to": dest}


@app.post("/auth/admin-reset-code")
def auth_admin_reset_code(login: str = Body(..., embed=True), db: Session = Depends(get_db), _admin: UserModel = Depends(require_admin)):
    """Admin: make a reset code for someone who cannot receive e-mail (no mail server configured, a
    wrong address, a token-only account). Returns the code so the admin can pass it on by hand; the
    person then uses «Ja tinc un codi». Also mailed when a mail server is configured."""
    key = (login or "").strip().lower()
    user = db.query(UserModel).filter((UserModel.email == key) | (UserModel.username == key)).first()
    if not user:
        raise HTTPException(status_code=404, detail="No hi ha cap compte amb aquest correu o nom d'usuari")
    code = f"{secrets.randbelow(10**6):06d}"
    user.reset_code_hash = _hash_token(code); user.reset_expires = datetime.utcnow() + timedelta(hours=2)
    db.commit()
    mailed = False
    try:  # an account with no address is recovered by the code alone, handed over by the admin
        mailed = bool(user.email) and bool(_send_email(user.email, "Tamazight Drills: codi per restablir la contrasenya",
                                  f"Hola {user.display_name or user.username},\n\nEl teu codi és: {code}\nCaduca en 2 hores.\n"))
    except Exception as e:
        print(f"[AUTH] admin reset e-mail failed: {e}")
    return {"username": user.username, "email": user.email or "", "code": code, "expires_in_hours": 2, "mailed": mailed}


@app.post("/auth/reset")
def auth_reset(request: Request, code: str = Body(..., embed=True), new_password: str = Body(..., embed=True),
               email: Optional[str] = Body(None, embed=True), login: Optional[str] = Body(None, embed=True),
               device: Optional[str] = Body(None, embed=True), db: Session = Depends(get_db)):
    """A new password from a 6-digit code. Who you are is your e-mail OR your user name: an account
    with no address is recovered with a code the admin hands over. Changing the password closes
    every other session, so a borrowed or stolen one dies here."""
    ip = request.client.host if request.client else "unknown"
    _rate_limit(_login_attempts, ip, 20, 900)
    key = (login or email or "").strip().lower()
    user = db.query(UserModel).filter((UserModel.email == key) | (UserModel.username == key)).first() if key else None
    if not user or not user.reset_code_hash or not user.reset_expires or user.reset_expires < datetime.utcnow() \
            or user.reset_code_hash != _hash_token((code or "").strip()):
        raise HTTPException(status_code=400, detail="Codi incorrecte o caducat")
    _check_password_strength(new_password)
    user.password_hash = _hash_password(new_password); user.reset_code_hash = None; user.reset_expires = None
    db.query(UserSessionModel).filter(UserSessionModel.user_id == user.id).delete()
    db.commit()
    return {**_user_payload(user), "token": _new_session(db, user, device)}


def _contributions(db, user, limit: int = 60) -> dict:
    """What a person has given the library: the drills they created, their takes (with their own
    words when they differ), the petitions they asked, the lesson changes accepted."""
    drills = db.query(DrillModel).filter(DrillModel.created_by_user_id == user.id).order_by(DrillModel.id.desc()).all()
    takes = (db.query(RecordingModel, DrillModel).join(DrillModel, DrillModel.id == RecordingModel.drill_id)
             .filter(RecordingModel.user_id == user.id).order_by(RecordingModel.id.desc()).all())
    accepted = db.query(LessonProposalModel).filter(LessonProposalModel.user_id == user.id, LessonProposalModel.status == "accepted").count()
    pending = db.query(LessonProposalModel).filter(LessonProposalModel.user_id == user.id, LessonProposalModel.status == "pending").count()
    row = lambda d: {"id": d.id, "text_tachelhit": d.text_tachelhit, "text_catalan": d.text_catalan, "audio_url": normalize_media_url(d.audio_url) if d.audio_url else None,
                     "image_url": d.image_url, "region": d.region, "variety": d.variety, "tag": d.tag, "variant_of": d.variant_of, "verified": d.verified,
                     "date_created": d.date_created.isoformat() if d.date_created else None}
    return {"counts": {"drills": len(drills), "petitions": sum(1 for d in drills if "petici" in (d.tag or "").lower()),
                       "variants": sum(1 for d in drills if d.variant_of), "takes": len(takes), "proposals_accepted": accepted, "proposals_pending": pending},
            "drills": [row(d) for d in drills[:limit]],
            "takes": [{"id": r.id, "audio_url": normalize_media_url(r.audio_url), "text": r.text, "variety": r.variety, "region": r.region,
                       "date_created": r.date_created.isoformat(), "drill": row(d)} for r, d in takes[:limit]]}


@app.get("/users/by-name/{username}")
def user_public_page(username: str, db: Session = Depends(get_db)):
    """A person's public page («fitxa»): who they are (name, town, variety, since when) and what they
    gave the library. No e-mail, no tokens."""
    user = db.query(UserModel).filter(UserModel.username == (username or "").strip().lower()).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"username": user.username, "display_name": user.display_name or user.username, "variety": user.variety, "region": user.region,
            "since": user.created_at.isoformat() if getattr(user, "created_at", None) else None, **_contributions(db, user)}


@app.get("/drills/{drill_id}/variants")
def drill_variants(drill_id: int, db: Session = Depends(get_db)):
    """The same sentence as other speakers say it: the original and every variant linked to it."""
    d = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Drill not found")
    root = db.query(DrillModel).filter(DrillModel.id == d.variant_of).first() if d.variant_of else d
    root = root or d
    variants = db.query(DrillModel).filter(DrillModel.variant_of == root.id).order_by(DrillModel.id.asc()).all()
    return {"original": Drill.model_validate(root, from_attributes=True), "variants": [Drill.model_validate(v, from_attributes=True) for v in variants]}


@app.get("/users/me")
def get_me(user: Optional[UserModel] = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Missing or invalid X-User-Token")
    drills_contributed = db.query(DrillModel).filter(DrillModel.created_by_user_id == user.id).count()
    cards_learning = db.query(DrillReviewModel).filter(DrillReviewModel.user_id == user.id).count()
    return {
        "id": user.id,            # so the app can tell whose a sentence is, as may_change does
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "is_admin": bool(user.is_admin),
        "has_password": bool(user.password_hash),
        "variety": user.variety,
        "region": user.region,
        "is_native": user.is_native,
        "tz": user.tz or DEFAULT_TZ,
        "date_created": iso_z(user.date_created),
        "drills_contributed": drills_contributed,
        "contributions": _contributions(db, user, limit=40),
        "cards_learning": cards_learning
    }


@app.put("/users/me")
def update_me(
    display_name: Optional[str] = Body(None, embed=True),
    variety: Optional[str] = Body(None, embed=True),
    region: Optional[str] = Body(None, embed=True),
    tz: Optional[str] = Body(None, embed=True),
    is_native: Optional[bool] = Body(None, embed=True),
    user: Optional[UserModel] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the contributor's own profile (display name, variety, region,
    tz = IANA zone for streak days). Only fields that are sent are changed."""
    if not user:
        raise HTTPException(status_code=401, detail="Missing or invalid X-User-Token")
    if display_name is not None:
        user.display_name = display_name.strip() or user.username
    if variety is not None:
        user.variety = variety or None
    if region is not None:
        user.region = region.strip() or None
    if is_native is not None:
        user.is_native = bool(is_native)
    if tz is not None:
        tz = tz.strip()
        if tz:
            try:
                ZoneInfo(tz)
            except Exception:
                raise HTTPException(status_code=400, detail=f"Unknown time zone: {tz}")
        user.tz = tz or None
    db.commit()
    db.refresh(user)
    return {"username": user.username, "display_name": user.display_name,
            "variety": user.variety, "region": user.region, "tz": user.tz or DEFAULT_TZ}


@app.post("/drills/{drill_id}/recordings")
async def add_recording(
    drill_id: int,
    file: UploadFile = File(...),
    variety: Optional[str] = Form(None),
    region: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    is_native: Optional[bool] = Form(None),
    db: Session = Depends(get_db),
    user: Optional[UserModel] = Depends(get_current_user),
):
    """Add one speaker's audio take of a drill. The take keeps the speaker's
    variety/region (defaulting to their declared profile), so the same drill can
    hold recordings from different people/varieties. `text` is the sentence as this
    speaker says it: kept only when it differs from the drill's own words, so the drill
    shows the sentence in every dialect that recorded it."""
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
    own_words = (text or "").strip()
    if own_words and own_words == (drill.text_tachelhit or "").strip():
        own_words = ""
    if variety and variety not in _VARIETY_CODES:
        raise HTTPException(status_code=400, detail="Varietat desconeguda")
    content = await file.read()
    up = await run_in_threadpool(
        cloudinary.uploader.upload,
        content, resource_type="auto", folder="tachelhit/recordings",
        public_id=f"rec_{drill_id}_{int(datetime.utcnow().timestamp())}",
    )
    url = normalize_media_url(up["secure_url"])
    rec = RecordingModel(
        drill_id=drill_id,
        user_id=user.id if user else None,
        audio_url=url,
        variety=(variety or (user.variety if user else None)),
        region=((region or "").strip() or (user.region if user else None)),
        speaker=((user.display_name or user.username) if user else None),
        # whose voice this is matters: a learner's take must never pass for a model pronunciation
        is_native=(is_native if is_native is not None else (user.is_native if user else None)),
        text=own_words or None,
    )
    db.add(rec)
    # La primera veu d'una frase muda passa a ser la seva veu principal — amb UNA condició que
    # ens han posat els auditors i que val la pena: la d'algú que APRÈN, no.
    #
    # No és un judici sobre ningú: `drill.audio_url` és el que sona al Mètode, el que sona a la
    # pràctica i el que `compare_words` fa servir de REFERÈNCIA per puntuar la pronunciació de
    # tothom. Una primera presa d'algú que aprèn es convertiria en l'objectiu que els altres han
    # d'encertar. La gravació hi és igual, i s'escolta igual; el que no fa és manar.
    learner = rec.is_native is False
    if not (drill.audio_url or "").strip() and not learner:
        drill.audio_url = url
    # a petition (Catalan only) gets its Tamazight from the first speaker who answers it, in their
    # own spelling; their variety and town travel with it.
    #
    # Mai, però, a una línia del manual: si s'hi copiés, hauríem reescrit el text d'El Mountassir
    # amb una forma de l'Atles mentre el peu segueix dient «Basat en El Mountassir». Aquelles
    # línies reben VEU —que és el que els falta— i frases nostres al costat, però el text no se'ls
    # toca des d'una gravació (ADR 0004).
    from_book = "del llibre" in (drill.tag or "")
    variant = None
    if not (drill.text_tachelhit or "").strip() and (text or "").strip() and not from_book:
        drill.text_tachelhit = (text or "").strip()
        drill.variety = drill.variety or rec.variety
        drill.region = drill.region or rec.region
        drill.speaker = drill.speaker or rec.speaker
    elif own_words:
        # the speaker says it with other words: their version becomes a card of its own, linked to
        # this one (same meaning, their text, their voice, their town), unless that exact wording
        # already exists as a variant
        existing = db.query(DrillModel).filter(DrillModel.variant_of == drill.id, DrillModel.text_tachelhit == own_words).first()
        if existing is None and own_words.lower() != (drill.text_tachelhit or "").strip().lower():
            variant = DrillModel(text_tachelhit=own_words, text_catalan=drill.text_catalan, text_arabic=drill.text_arabic,
                                 audio_url=url, image_url=drill.image_url, image_credit=drill.image_credit,
                                 tag=", ".join(x for x in [(drill.tag or "").strip(), "variant"] if x), variant_of=drill.id,
                                 variety=rec.variety, region=rec.region, speaker=rec.speaker, created_by_user_id=user.id if user else None,
                                 grammar=drill.grammar, grammar_source=drill.grammar_source, topics=drill.topics, topics_source=drill.topics_source,
                                 license=drill.license, verified=False)
            db.add(variant)
        else:
            variant = existing
    db.commit()
    db.refresh(rec)
    if variant is not None:
        db.refresh(variant)
    return {"id": rec.id, "audio_url": rec.audio_url, "variety": rec.variety,
            "region": rec.region, "speaker": rec.speaker, "text": rec.text,
            "date_created": rec.date_created.isoformat(),
            "variant_id": variant.id if variant is not None else None}


@app.post("/drills/{drill_id}/variant", response_model=Drill)
def add_variant(drill_id: int, text_tachelhit: str = Body(..., embed=True),
                note: Optional[str] = Body(None, embed=True),
                variety: Optional[str] = Body(None, embed=True), region: Optional[str] = Body(None, embed=True),
                user: UserModel = Depends(require_user), db: Session = Depends(get_db)):
    """Say it your way. The sentence is copied as a second version linked to the first: the Catalan
    meaning is the original's — that is what makes them the same sentence — and the Tamazight is
    yours, in your spelling, with your variety and your region on it. Nothing of the original
    changes, and the new one belongs to whoever wrote it."""
    original = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Drill not found")
    said = (text_tachelhit or "").strip()
    if len(said) < 2:
        raise HTTPException(status_code=400, detail="Escriu com ho dius tu")
    if said.lower() == (original.text_tachelhit or "").strip().lower():
        raise HTTPException(status_code=409, detail="Això és igual que el que ja hi ha")
    root = original.variant_of or original.id   # variants of a variant still hang on the first one
    variant = DrillModel(
        text_catalan=original.text_catalan, text_tachelhit=said, text_arabic=original.text_arabic,
        image_url=original.image_url, variant_of=root, created_by_user_id=user.id,
        variety=(variety or user.variety), region=((region or "").strip() or user.region),
        author=(user.display_name or user.username), notes=(note or None),
        tag=", ".join(x for x in [(original.tag or "").strip(), "variant"] if x) or "variant",
        grammar=original.grammar, topics=original.topics,
    )
    db.add(variant); db.commit(); db.refresh(variant)
    return variant


@app.get("/drills/{drill_id}/recordings")
def list_recordings(drill_id: int, db: Session = Depends(get_db)):
    """All takes of a drill, oldest first, each with its speaker/variety."""
    recs = (db.query(RecordingModel)
            .filter(RecordingModel.drill_id == drill_id)
            .order_by(RecordingModel.date_created.asc()).all())
    return [{"id": r.id, "audio_url": normalize_media_url(r.audio_url),
             "variety": r.variety, "region": r.region, "speaker": r.speaker, "text": r.text,
             "is_native": r.is_native,   # a native speaker's voice, a learner's, or not said
             "license": r.license, "date_created": r.date_created.isoformat()} for r in recs]


@app.patch("/recordings/{recording_id}")
def update_recording(recording_id: int, text: Optional[str] = Body(None, embed=True),
                     variety: Optional[str] = Body(None, embed=True), region: Optional[str] = Body(None, embed=True),
                     db: Session = Depends(get_db), user: Optional[UserModel] = Depends(get_current_user)):
    """Fix a take's own wording, variety or town. The recorder (or an admin) only."""
    r = db.query(RecordingModel).filter(RecordingModel.id == recording_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recording not found")
    if r.user_id and not (user and (user.id == r.user_id or user.is_admin)):
        raise HTTPException(status_code=403, detail="Només qui va gravar la veu (o un administrador) la pot editar")
    if text is not None:
        drill = db.query(DrillModel).filter(DrillModel.id == r.drill_id).first()
        t = text.strip()
        r.text = t if t and t != ((drill.text_tachelhit or "").strip() if drill else "") else None
    if variety is not None:
        if variety and variety not in _VARIETY_CODES:
            raise HTTPException(status_code=400, detail="Varietat desconeguda")
        r.variety = variety or None
    if region is not None:
        r.region = region.strip() or None
    db.commit()
    return {"id": r.id, "text": r.text, "variety": r.variety, "region": r.region}


@app.delete("/recordings/{recording_id}")
def delete_recording(recording_id: int, db: Session = Depends(get_db),
                     user: Optional[UserModel] = Depends(get_current_user)):
    r = db.query(RecordingModel).filter(RecordingModel.id == recording_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recording not found")
    db.delete(r)
    db.commit()
    return {"deleted": recording_id}

@app.post("/drills/{drill_id}/verify")
def verify_drill(drill_id: int, verified: bool = Body(True, embed=True),
                 db: Session = Depends(get_db),
                 user: Optional[UserModel] = Depends(get_current_user)):
    """
    Contribution review (auditor Phase 3): a registered user marks a drill's
    text/audio as verified (or revokes it). Verified items are what the
    corpus flywheel exports for model fine-tuning.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Verification requires a registered user (X-User-Token)")
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
    drill.verified = bool(verified)
    drill.verified_by_user_id = user.id if verified else None
    db.commit()
    return {"drill_id": drill_id, "verified": drill.verified, "verified_by": user.username if verified else None}

@app.get("/version")
def get_version():
    """
    Deploy verification: Render injects RENDER_GIT_COMMIT automatically, so
    this answers 'which code is production actually running?' at a glance.
    """
    return {
        "commit": os.getenv("RENDER_GIT_COMMIT", "local"),
        "features": {
            "capture_import_url": True,
            "auto_drills_pipeline": True,
            "lyrics_alignment": True,
            "ocr": bool(os.getenv("HUGGINGFACE_OCR_SPACE_URL")),
            "srs": True,
            "tachelhit_tts_fallback": True,
            "users": True,
            "corpus": True,
            "api_key_gate": bool((os.getenv("API_KEY") or "").strip()),
        }
    }

# ===================== AI AGENT (Gemini grammar tutor) =====================

_GRAMMAR_TEXT = None

def _load_grammar() -> str:
    """
    Load the Amazigh grammar reference once (cached in memory). The text is not
    committed to the repo (third-party material); build_grammar() generates it
    from the public amazic.cat PDFs on first use.
    """
    global _GRAMMAR_TEXT
    if _GRAMMAR_TEXT is None:
        try:
            from build_knowledge import build_grammar
            path = build_grammar()  # generates the file if missing
            with open(path, "r", encoding="utf-8") as f:
                _GRAMMAR_TEXT = f.read()
        except Exception as e:
            print(f"[AI] Could not load/build grammar reference: {e}")
            _GRAMMAR_TEXT = ""
    return _GRAMMAR_TEXT

AI_SYSTEM_ROLE = """Ets l'assistent lingüístic de "Tamazight Drills", una aplicació per aprendre la llengua amaziga taixelhit (tachelhit/tashelhit) fent servir el català com a llengua de referència, amb l'àrab i els alfabets tifinag i llatí.

El teu paper:
- Ajudes qui aprèn a entendre la gramàtica, la pronunciació i l'ús del taixelhit i l'amazic en general.
- Et bases SEMPRE en el "Compendi de Gramàtica Amaziga" que tens a continuació com a font principal. Cita la secció (p. ex. "§5. Morfosintaxi verbal") quan sigui rellevant.
- Si la pregunta va sobre un drill concret de l'usuari, fes servir el seu contingut (català, taixelhit en tifinag i llatí, àrab) per explicar-lo.
- Si el compendi no cobreix una cosa, digues-ho clarament i aporta el teu millor coneixement lingüístic, marcant-ho com a complement.
- Quan el context d'un drill porta línies marcades [Oulhaj] (diccionari anglès–taixelhit de Lahcen Oulhaj) o [IRCAM] (taules de conjugació de l'IRCAM), són dades de referència: per a una paraula amb la mateixa grafia tenen prioritat sobre el que recordis, i les cites amb aquesta marca. Les línies marcades «coincidència aproximada de grafia» només són pistes (el diccionari és del taixelhit del Sus; en Atles Central la mateixa grafia pot ser una altra paraula): descarta-les quan no quadrin amb el significat català.
- Respon en la llengua de la pregunta (per defecte català). Sigues clar, concret i pedagògic. Fes servir exemples.

PRINCIPI DE VARIETAT (molt important): qui aprèn documenta una varietat regional concreta (sovint tamazight de l'Atles central, zona Azilal–Kalaat Mgouna), que NO és idèntica al taixelhit del Sus ni al tamazight estàndard de l'IRCAM. Quan la forma ATTESTADA (recollida per l'usuari d'un parlant real) difereixi de l'estàndard o del compendi, la forma attestada és la correcta per a aquella varietat: explica la diferència, no la "corregeixis" cap a l'estàndard. Tracta les formes recollides per l'usuari com a dades de camp valuoses.

=== COMPENDI DE GRAMÀTICA AMAZIGA (font: amazic.cat) ===
"""

def _attested_forms_context(db, limit: int = 40) -> str:
    """
    A compact block of the learner's own collected forms (preferring verified),
    so the AI grounds in the actual variety being documented, not just the
    general grammar.
    """
    from sqlalchemy import and_
    q = (db.query(DrillModel)
         .filter(and_(DrillModel.text_tachelhit != None, DrillModel.text_tachelhit != ''))
         .order_by(DrillModel.verified.isnot(None).desc(), DrillModel.date_created.desc())
         .limit(limit).all())
    if not q:
        return ""
    lines = []
    for d in q:
        parts = [f"tam: {d.text_tachelhit}"]
        if d.text_tachelhit_latin: parts.append(f"llatí: {d.text_tachelhit_latin}")
        if d.text_catalan: parts.append(f"cat: {d.text_catalan}")
        if d.variety: parts.append(f"varietat: {d.variety}")
        lines.append("- " + " | ".join(parts))
    return ("\n\n=== FORMES ATTESTADES RECOLLIDES PER L'USUARI (dades de camp, prioritàries) ===\n"
            + "\n".join(lines))

def _build_system_instruction(db) -> str:
    """Role + grammar compendium + the learner's attested corpus."""
    return AI_SYSTEM_ROLE + _load_grammar() + _attested_forms_context(db)

def _drill_context(drill) -> str:
    if not drill:
        return ""
    fields = [
        ("Català", drill.text_catalan),
        ("Taixelhit (tifinag)", drill.text_tachelhit),
        ("Taixelhit (llatí)", drill.text_tachelhit_latin),
        ("Àrab", drill.text_arabic),
        ("Etiqueta de catàleg (nom del vídeo o de la col·lecció; NO és text del drill)", drill.tag),
        ("Varietat", drill.variety),
        ("Regió", drill.region),
    ]
    lines = [f"- {label}: {val}" for label, val in fields if val]
    sug = (getattr(drill, "text_tachelhit_suggested", None) or "").strip()
    if sug and not (drill.text_tachelhit or "").strip():
        st = draft_status(getattr(drill, "draft_check", None), sug)
        if st == "no":
            lines.append("- Esborrany automàtic: n'hi ha un, però la comprovació de significat diu que NO quadra amb la traducció "
                         "(no són paraules amazigues reals o diuen una altra cosa). NO l'expliquis: digues que cal la transcripció "
                         "d'un parlant i explica només el significat català/àrab.")
        else:
            lines.append(f"- Esborrany automàtic (lectura de màquina, NO confirmada per cap parlant; «[? a | b]» = insegur"
                         + ("; la comprovació de significat diu que quadra aproximadament" if st == "roughly" else "") + f"): {sug}")
    if not (drill.text_tachelhit or "").strip() and not sug:
        lines.append("- Taixelhit: encara no hi ha transcripció d'aquest drill")
    lines.append("La FRASE del drill és la del camp Taixelhit (o, si no n'hi ha, l'esborrany); el català n'és el significat.")
    phrase = (drill.text_tachelhit or "").strip() or (drill.text_tachelhit_latin or "").strip() or sug
    ground = lexicon.grounding_lines(phrase) if phrase else []
    if ground:
        lines.append("DICCIONARI I CONJUGACIONS per a les paraules d'aquesta frase (fes-los servir abans que la teva memòria; "
                     "cita [Oulhaj] o [IRCAM]):")
        lines.extend(ground)
    lines.append("REGLA: explica només el text que hi ha. Si només hi ha l'esborrany, treballa sobre l'esborrany i digues que és "
                 "un esborrany. MAI inventis ni proposis una frase en taixelhit com si fos la del drill.")
    return "DRILL SELECCIONAT:\n" + "\n".join(lines) if lines else ""

@app.get("/catalog/topics")
def catalog_topics():
    """The subject vocabulary with, per subject, how many drills carry it."""
    return {"topics": topics_catalog.TOPICS, "counts": topics_catalog.counts(SessionLocal), "status": topics_catalog.status()}


@app.post("/catalog/topics/run")
def catalog_topics_run(force: bool = False, limit: int = 2000, ids: Optional[str] = None):
    """Classify drills without subjects (all auto-classified ones with force) in the background."""
    only = [int(x) for x in ids.split(",") if x.strip().isdigit()] if ids else None
    if topics_catalog.status()["running"]:
        return {"started": False, "reason": "already running", **topics_catalog.status()}
    threading.Thread(target=topics_catalog.run, args=(SessionLocal, force, limit, only), daemon=True).start()
    return {"started": True}


@app.get("/catalog/topics/status")
def catalog_topics_status():
    return topics_catalog.status()


# ===================== GRAMMAR COURSE =====================
@app.post("/drills/{drill_id}/voice-wanted")
def ask_for_a_voice(drill_id: int, wanted: bool = Body(True, embed=True),
                    user: UserModel = Depends(require_user), db: Session = Depends(get_db)):
    """Mark a sentence as one our speakers should say out loud, from the lesson card where you
    noticed it. Marked sentences go to the top of the «Veus» list."""
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
    drill.voice_wanted = bool(wanted)
    drill.voice_wanted_by = ((user.display_name or user.username) if wanted else None)
    db.commit()
    return {"id": drill.id, "voice_wanted": bool(drill.voice_wanted), "voice_wanted_by": drill.voice_wanted_by}


@app.post("/drills/voice-wanted/missing")
def ask_for_every_missing_voice(include_synthetic: bool = Body(True, embed=True),
                                user: UserModel = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin: ask our speakers for EVERY sentence the library cannot say out loud. One pass in the
    database instead of hundreds of calls from outside. A sentence that already has a human take
    (its own or somebody else's) is left alone; a synthetic voice does not count as said."""
    taken = {r[0] for r in db.query(RecordingModel.drill_id).all()}
    rows = grammar_course.not_excluded(
        db.query(DrillModel).filter((DrillModel.audio_url.is_(None)) | (DrillModel.audio_url == "")), DrillModel).all()
    who = (user.display_name or user.username)
    n = 0
    for d in rows:
        if d.id in taken or not (d.text_tachelhit or "").strip():
            continue
        if not include_synthetic and (d.audio_tts_shi_url or "").strip():
            continue
        if not d.voice_wanted:
            d.voice_wanted, d.voice_wanted_by = True, who
            n += 1
    db.commit()
    return {"asked": n, "already_asked": sum(1 for d in rows if d.voice_wanted) - n, "with_a_take": len(taken)}


# ===================== VEUS: petitions and recordings wanted =====================
def _petition_row(d, units_level: dict) -> dict:
    us = grammar_course.parse(d.grammar)
    return {"drill": Drill.model_validate(d, from_attributes=True), "units": us,
            "level": min([units_level.get(u, 9) for u in us] or [9]), "requested_by": d.requested_by, "note": d.requested_note}


@app.get("/petitions")
def petitions(kind: str = "open", limit: int = 40, offset: int = 0, topic: Optional[str] = None,
              unit: Optional[str] = None, db: Session = Depends(get_db)):
    """What the community can record. `open`: sentences a learner asked for, still without Tamazight
    (a speaker answers with their recording and their own spelling). `synthetic`: drills that have a
    text but no human voice yet (only a synthetic one), the basic units first. `aitmraw`: the
    sentences our Aït Mraw speakers could say in their words (the course's wishlist)."""
    units_level = {u["slug"]: u["level"] for u in grammar_course.UNITS}
    base = grammar_course.not_excluded(db.query(DrillModel), DrillModel)
    if kind == "open":
        rows = base.filter(DrillModel.tag.ilike("%petici%"), (DrillModel.text_tachelhit.is_(None)) | (DrillModel.text_tachelhit == "")).order_by(DrillModel.id.desc()).all()
        return {"items": [_petition_row(d, units_level) for d in rows[:max(1, min(limit, 200))]], "total": len(rows)}
    if kind == "synthetic":
        # every real drill nobody has recorded yet: the synthetic voice is only scaffolding
        rows = base.filter(DrillModel.text_tachelhit.isnot(None), DrillModel.text_tachelhit != "", DrillModel.text_catalan.isnot(None),
                           (DrillModel.audio_url.is_(None)) | (DrillModel.audio_url == "")).all()
        rows = [d for d in rows if grammar_course.quotable(d.text_tachelhit, (grammar_course.parse(d.grammar) or [None])[0])]
        if topic:
            rows = [d for d in rows if topic in topics_catalog.parse(d.topics)]
        if unit:
            rows = [d for d in rows if unit in grammar_course.parse(d.grammar)]
        items = [_petition_row(d, units_level) for d in rows]
        # the course's first units first, then the ones with a picture to record from
        items.sort(key=lambda x: (x["level"], not x["drill"].image_url, -x["drill"].id))
        return {"items": items[max(0, offset):max(0, offset) + max(1, min(limit, 200))], "total": len(items),
                "without_any_voice": sum(1 for x in items if not x["drill"].audio_tts_shi_url)}
    if kind == "voiceless":
        # TOTES les que ningú no ha dit mai, sense triar-ne cap: l'amo va trobar a faltar
        # justament la llista sencera. «synthetic» és aquesta mateixa llista, però filtrada pel
        # que el curs pot citar i ordenada per unitats; aquesta no amaga res.
        rows = base.filter(DrillModel.text_tachelhit.isnot(None), DrillModel.text_tachelhit != "",
                           (DrillModel.audio_url.is_(None)) | (DrillModel.audio_url == "")).order_by(
                               DrillModel.image_url.isnot(None).desc(), DrillModel.id.desc()).all()
        if topic:
            rows = [d for d in rows if topic in topics_catalog.parse(d.topics)]
        if unit:
            rows = [d for d in rows if unit in grammar_course.parse(d.grammar)]
        items = [_petition_row(d, units_level) for d in rows]
        return {"items": items[max(0, offset):max(0, offset) + max(1, min(limit, 200))], "total": len(items)}
    if kind == "untranscribed":
        # Veus que ningú no ha escrit. És l'altra meitat de la feina i no es veia enlloc: una
        # gravació sense text no es pot buscar, ni citar, ni entrar a cap lliçó — i qui la va
        # dir ja ha fet la part difícil.
        rows = base.filter(DrillModel.audio_url.isnot(None), DrillModel.audio_url != "",
                           (DrillModel.text_tachelhit.is_(None)) | (DrillModel.text_tachelhit == "")).order_by(
                               DrillModel.id.desc()).all()
        items = [_petition_row(d, units_level) for d in rows]
        return {"items": items[max(0, offset):max(0, offset) + max(1, min(limit, 200))], "total": len(items)}
    if kind == "aitmraw":
        w = grammar_wishlist(per_unit=6, db=db)["units"]
        items = [{"drill": d, "units": [u["slug"]], "level": u["level"], "requested_by": None, "note": f"Unitat «{u['title']}»: {u['aitmraw_voiced']} veus d'Aït Mraw"} for u in w for d in u["wanted"]]
        return {"items": items[:max(1, min(limit, 200))], "total": len(items)}
    raise HTTPException(status_code=400,
                        detail="kind must be open, synthetic, voiceless, untranscribed or aitmraw")


@app.post("/petitions")
def add_petition(text_catalan: str = Body(..., embed=True), note: Optional[str] = Body(None, embed=True),
                 db: Session = Depends(get_db), user: UserModel = Depends(require_user)):
    """A learner asks how to say something: a drill with the Catalan only, tagged «petició», that a
    native speaker completes by recording it with their own words."""
    t = (text_catalan or "").strip()
    if len(t) < 2:
        raise HTTPException(status_code=400, detail="Escriu què vols saber dir")
    d = DrillModel(text_catalan=t, text_tachelhit="", tag="petició", requested_by=(user.display_name or user.username),
                   requested_note=(note or "").strip() or None, created_by_user_id=user.id, grammar_source="auto", topics_source="auto")
    db.add(d); db.commit(); db.refresh(d)
    return Drill.model_validate(d, from_attributes=True)


@app.get("/grammar/{slug}/proposals")
def lesson_proposals(slug: str, db: Session = Depends(get_db), user: Optional[UserModel] = Depends(get_current_user)):
    """The pending proposals for a lesson: all of them for an admin, their own for anyone else."""
    q = db.query(LessonProposalModel).filter(LessonProposalModel.slug == slug, LessonProposalModel.status == "pending")
    if not (user and user.is_admin):
        q = q.filter(LessonProposalModel.user_id == (user.id if user else -1))
    return [{"id": p.id, "slug": p.slug, "step": p.step, "kind": p.kind, "text": p.text, "display_name": p.display_name, "region": p.region,
             "status": p.status, "created_at": p.created_at.isoformat()} for p in q.order_by(LessonProposalModel.id.desc()).all()]


#: Una proposta per a un capítol del Mètode porta el capítol al davant: «metode:la-botiga».
#:
#: És la mateixa cua de propostes que la del curs de gramàtica, i ha de ser-ho: qui llegeix veu
#: una explicació i hi vol dir alguna cosa, tant li fa de quina part de l'app sigui. El que
#: canvia és on s'escriu quan s'accepta, i això ho decideix aquest prefix.
METHOD_PROPOSAL = "metode:"


def _proposal_target(slug: str) -> str:
    """De quina part de l'app és aquesta proposta: «grammar» o «method». 404 si no existeix."""
    if slug.startswith(METHOD_PROPOSAL):
        if not method_mod.chapter(slug[len(METHOD_PROPOSAL):]):
            raise HTTPException(status_code=404, detail="Aquest capítol no existeix")
        return "method"
    if slug not in grammar_course.TITLES:
        raise HTTPException(status_code=404, detail="Unit not found")
    return "grammar"


@app.post("/grammar/{slug}/proposals")
def propose_lesson_change(slug: str, step: int = Body(..., embed=True), text: str = Body(..., embed=True), kind: str = Body("text", embed=True),
                          db: Session = Depends(get_db), user: UserModel = Depends(require_user)):
    """A learner or speaker proposes a change to a card (step index; -1 = the intro): a new text,
    or a note. Kept for an admin to accept or reject.

    The slug is a grammar unit, or a Method chapter written «metode:la-botiga» — same queue, and
    the step is then the section's place in the chapter."""
    _proposal_target(slug)
    t = (text or "").strip()
    if len(t) < 3:
        raise HTTPException(status_code=400, detail="Escriu la proposta")
    p = LessonProposalModel(slug=slug, step=int(step), kind=("note" if kind == "note" else "text"), text=t, user_id=user.id,
                            display_name=(user.display_name or user.username), region=user.region)
    db.add(p); db.commit(); db.refresh(p)
    return {"id": p.id, "status": p.status}


@app.post("/grammar/proposals/{proposal_id}/decide")
def decide_lesson_proposal(proposal_id: int, accept: bool = Body(..., embed=True), db: Session = Depends(get_db), _admin: UserModel = Depends(require_admin)):
    """Admin: accept (the text replaces the card's text in the stored lesson) or reject a proposal."""
    from models import GrammarLesson
    p = db.query(LessonProposalModel).filter(LessonProposalModel.id == proposal_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found")
    if accept and p.kind == "text" and p.slug.startswith(METHOD_PROPOSAL):
        chapter = p.slug[len(METHOD_PROPOSAL):]
        body = method_mod.content_of(db, chapter)
        if not body:
            raise HTTPException(status_code=409, detail="Aquest capítol encara no té text")
        sections = body.get("sections") or []
        if p.step == -1:
            body["intro"] = p.text
        elif 0 <= p.step < len(sections):
            sections[p.step]["text"] = p.text
        else:
            raise HTTPException(status_code=409, detail="Aquesta secció ja no hi és")
        method_mod.store_content(db, chapter, body, who=f"proposta de {p.display_name or 'algú'}")
    elif accept and p.kind == "text":
        row = db.query(GrammarLesson).filter(GrammarLesson.id == p.slug).first()
        if not row:
            raise HTTPException(status_code=409, detail="The lesson is not written yet")
        lesson = json.loads(row.body)
        if p.step == -1:
            lesson["intro"] = p.text
        elif 0 <= p.step < len(lesson.get("steps", [])) and "text" in lesson["steps"][p.step]:
            lesson["steps"][p.step]["text"] = p.text
        else:
            raise HTTPException(status_code=409, detail="That card no longer exists in the lesson")
        row.body = json.dumps(lesson, ensure_ascii=False); row.updated_at = datetime.utcnow()
    p.status = "accepted" if accept else "rejected"
    db.commit()
    return {"id": p.id, "status": p.status}


# ===================== PRÀCTICA (pronunciation sessions) =====================
# ===================== HISTORIES I CANÇONS ====================
@app.get("/stories")
def list_stories(db: Session = Depends(get_db)):
    """Whole stories and songs the library already holds (#189).

    Not a new kind of row: a story is what a group of drills already is when they come from one
    source and say when they are spoken. The ones you can read all the way through come first.
    """
    return {"stories": stories_mod.listing(db)}


@app.get("/stories/{slug}")
def read_story(slug: str, db: Session = Depends(get_db)):
    """One story: its lines in the order they are spoken, each with its voice and meaning.

    A line whose Amazigh words nobody has written down is kept in its place and marked. A story
    with holes is still a story, and the hole says what is missing instead of hiding it.
    """
    story = stories_mod.one(db, slug)
    if not story:
        raise HTTPException(status_code=404, detail="Aquesta hist\u00f2ria no existeix")
    ids = story.pop("drill_ids")
    rows = {d.id: d for d in db.query(DrillModel).filter(DrillModel.id.in_(ids)).all()}
    return {**story, "drills": [Drill.model_validate(rows[i], from_attributes=True) for i in ids if i in rows]}


# ===================== UNA PARAULA, DITA ====================
@app.get("/words/audio")
def word_audio_clips(word: str, limit: int = 6, db: Session = Depends(get_db)):
    """Where this word can be heard: a recording, and the two times it sits between.

    No new sound files. A word is a drill id and a span inside the recording that already exists,
    so the player seeks there. The people we can name come first; the open corpus only fills the
    gaps they leave, and every clip says which it is.
    """
    clips = word_audio.clips_for(db, word, limit=max(1, min(limit, 20)))
    return {"word": word, "count": len(clips), "clips": clips}


@app.get("/words/align/status")
def word_align_status():
    """How the alignment pass is going."""
    from models import WordAudio
    db = SessionLocal()
    try:
        return {**word_audio.state(),
                "stored": db.query(WordAudio).count(),
                "recordings": db.query(WordAudio.drill_id).distinct().count()}
    finally:
        db.close()


@app.get("/asr/night/status")
def night_asr_status():
    """Com va la tanda de transcripcions, i quantes gravacions esperen."""
    from models import Drill as D
    db = SessionLocal()
    try:
        esperen = db.query(D).filter(
            D.audio_url.isnot(None), D.audio_url != "",
            (D.text_tachelhit.is_(None)) | (D.text_tachelhit == "")).count()
        proposades = db.query(D).filter(
            D.text_tachelhit_suggested.isnot(None), D.text_tachelhit_suggested != "",
            (D.text_tachelhit.is_(None)) | (D.text_tachelhit == "")).count()
        return {**night_asr.state(), "waiting": esperen, "proposed": proposades}
    finally:
        db.close()


@app.post("/asr/night/run")
def night_asr_run(limit: int = 50, redo: bool = False, _admin: UserModel = Depends(require_admin)):
    """Proposa el text de les gravacions que ningú no ha escrit.

    En un fil, com l'alineador i pel mateix motiu: el Space és una sola CPU i triga un minut per
    gravació. És pensat perquè ho cridi un rellotge de nit, no una persona esperant.

    El que surt no és el text del parlant: va a `text_tachelhit_suggested` amb la certesa al
    costat, i `text_tachelhit` es queda buit fins que algú ho confirma.
    """
    night_asr.run(SessionLocal, limit=limit, redo=redo)
    return {"started": True, **night_asr.state()}


@app.post("/words/align/run")
def word_align_run(limit: int = 200, redo: bool = False, _admin: UserModel = Depends(require_admin)):
    """Align recorded sentences so their words can be played one by one.

    On a thread: the Space is one CPU and takes one request at a time, and nobody should sit in
    front of a spinner while a few hundred recordings are listened to.
    """
    word_audio.run(SessionLocal, limit=limit, redo=redo)
    return {"started": True, **word_audio.state()}


# ===================== CREDITS =====================
_CREDITS_FALLBACK = (
    "# Cr\u00e8dits i fonts\n\n"
    "Aquesta app s'aguanta en feina d'altri: el **Compendi de Gram\u00e0tica Amaziga** d'amazic.cat "
    "(Carles M\u00farcia i Salem Zenia), el l\u00e8xic de l'**IRCAM** (DGLAI i les conjugacions, CC BY-NC 4.0), "
    "el transcriptor **ayymen/stt_zgh_fastconformer_ctc_small** (CC BY 4.0) amb l'alineador de "
    "**NVIDIA NeMo** (Apache 2.0), i els corpus de **Mozilla Common Voice** (CC0), **Tamazight NLP** "
    "(Apache 2.0) i el **projecte Awal / CIEMEN** (CC BY 4.0).\n\n"
    "La llista sencera, amb cada llic\u00e8ncia i la citaci\u00f3 que demana, \u00e9s a `docs/CREDITS.md` del "
    "repositori.\n"
)


@app.get("/credits")
def credits():
    """What the project owes to other people, read from docs/CREDITS.md.

    One file, one truth: a copy inside the app would drift away from the one that is maintained.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    for path in (os.path.join(here, "..", "docs", "CREDITS.md"),
                 os.path.join(here, "docs", "CREDITS.md")):
        try:
            with open(os.path.normpath(path), encoding="utf-8") as f:
                return {"markdown": f.read(), "source": "docs/CREDITS.md"}
        except OSError:
            continue
    return {"markdown": _CREDITS_FALLBACK, "source": "fallback"}


@app.get("/method/")
def method_index(db: Session = Depends(get_db),
                 user: Optional[UserModel] = Depends(get_current_user)):
    """Els deu capítols del Mètode, i quant en tenim recollit de cadascun.

    La barra de cada capítol NO és el progrés de qui aprèn: és quantes frases nostres fan el que
    el capítol demana. Un capítol curt vol dir que d'allò encara no n'hem gravat, i és l'argument
    per anar-hi. Vegeu ADR 0003: del manual se'n pren el pla, mai el text.
    """
    drawn = artwork(db, "method")
    out = []
    for c in method_mod.index():
        rows = method_mod.sentences_for(db, c["slug"])
        out.append({**c,
                    # el dibuix del capítol: diu de què va abans de llegir-ne una paraula
                    "cover": drawn.get(c["slug"]),
                    **method_mod.readiness(c, rows),
                    "written": method_mod.content_of(db, c["slug"]) is not None,
                    "sentences": len(rows),
                    "with_voice": sum(1 for d in rows if d.audio_url),
                    "varieties": sorted({(d.variety or "").strip() for d in rows if (d.variety or "").strip()})})
    return {"chapters": out, "source": method_mod.SOURCE}


def _another_way(said: Optional[str], written: Optional[str]) -> bool:
    """Si això que algú ha dit és de debò una altra manera de dir-ho, i no la mateixa escrita
    igual (o escrita amb gh en comptes de ɣ, que és la mateixa paraula)."""
    import practice as practice_mod
    key = lambda t: " ".join(practice_mod.sound_key(w) for w in practice_mod.words_of(t or ""))
    return bool((said or "").strip()) and key(said) != key(written)


def other_ways(db) -> Dict[int, List[dict]]:
    """Les altres maneres de dir una frase: les gravacions que porten el text de qui les diu.

    L'amo: «si jo gravo i canvio el text, el sistema hauria de mostrar també l'altra versió de la
    mateixa frase amb la seva gravació, i hauria de mostrar l'autor i la zona».

    Això ja existia a mitges: la gravadora pregunta «com ho dius tu?» i el que s'hi escriu es
    desa amb la gravació (`recordings.text`), però no es veia enlloc fora del reproductor. Una
    frase dita d'una altra manera no és una correcció de l'altra: són dues maneres, i totes dues
    porten el nom de qui la diu i el seu poble. La del llibre no mana sobre la del poble.

    Només surten les gravacions que PORTEN text propi: una gravació sense text és la mateixa
    frase amb una altra veu, i això ja ho diu el reproductor.
    """
    out: Dict[int, List[dict]] = {}
    rows = (db.query(RecordingModel)
            .filter(RecordingModel.text.isnot(None), RecordingModel.text != "")
            .order_by(RecordingModel.date_created.asc()).all())
    for r in rows:
        out.setdefault(r.drill_id, []).append({
            "id": r.id, "text": (r.text or "").strip(),
            "tif": grammar_course.tifinagh((r.text or "").strip()),
            "audio_url": normalize_media_url(r.audio_url),
            "speaker": r.speaker, "variety": r.variety, "region": r.region,
            "is_native": r.is_native,
        })
    return out


#: El capítol servit l'últim cop, i amb quina biblioteca es va fer.
#:
#: Servir un capítol vol dir llegir les mil sis-centes frases que hi poden anar i puntuar-les
#: secció per secció: deu segons. I no canvia entre una visita i la següent si no ha canviat ni
#: el text del capítol ni la biblioteca, així que es guarda fet i es torna a fer quan alguna de
#: les dues coses es mou. No hi ha res de qui mira: el capítol és el mateix per a tothom.
_CHAPTER_CACHE: Dict[str, tuple] = {}


def _library_mark(db, slug: str) -> tuple:
    """La marca del moment: quantes frases hi ha, l'última que s'ha tocat, i quan es va escriure
    el capítol. Si les tres són iguals, el capítol servit també ho és."""
    from sqlalchemy import func

    from models import MethodChapter
    n, last = db.query(func.count(DrillModel.id), func.max(DrillModel.updated_at)).one()
    row = db.query(MethodChapter.updated_at).filter(MethodChapter.slug == slug).first()
    # i el dibuix del capítol, que també és part del que es veu: sense això, canviar-lo no es
    # notava fins que es movia una frase (ho va ensenyar una prova que va fallar sola)
    art = db.query(AppSettingModel.updated_at).filter(AppSettingModel.key == "artwork_method").first()
    # i les pràctiques: la sortida del capítol apareix quan se'n crea una, no quan
    # es toca una frase
    pn, plast = db.query(func.count(TestModel.id), func.max(TestModel.updated_at)).one()
    return (n, str(last), str(row[0]) if row else None, str(art[0]) if art else None,
            pn, str(plast))


@app.get("/method/{slug}")
def method_chapter(slug: str, db: Session = Depends(get_db),
                   user: Optional[UserModel] = Depends(get_current_user)):
    """Un capítol: què en sabràs fer, les frases nostres que ho fan, i el que ens falta."""
    c = method_mod.chapter(slug)
    if not c:
        raise HTTPException(status_code=404, detail="Aquest capítol no existeix")
    mark = _library_mark(db, slug)
    done = _CHAPTER_CACHE.get(slug)
    if done and done[0] == mark:
        return done[1]
    rows = method_mod.sentences_for(db, c["slug"])
    titles = {u["slug"]: u["title"] for u in grammar_course.UNITS}
    labels = {t["slug"]: t["label"] for t in topics_catalog.TOPICS}
    said = other_ways(db)

    def card(d):
        return {"id": d.id, "text_tachelhit": d.text_tachelhit,
                "text_tachelhit_latin": d.text_tachelhit_latin,
                "text_catalan": d.text_catalan, "audio_url": d.audio_url,
                "image_url": d.image_url, "speaker": d.speaker or d.author,
                "variety": d.variety, "region": d.region,
                "grammar": d.grammar, "topics": d.topics,
                # D'on surt: una línia del manual gravada no és una atestació de l'Atles, i a la
                # pantalla s'han de poder distingir (ho va dir un auditor dialectòleg veient
                # «is trit aman?» sota «Dit per les nostres veus», sense parlant ni poble).
                "tag": d.tag,
                "from_book": "del llibre" in (d.tag or ""),
                # paraula per paraula, igual que al curs de gramàtica: una frase que s'ensenya
                # i no es pot desmuntar és una frase que només es pot repetir
                "gloss": grammar_course.gloss_of(d),
                "tif": grammar_course.tifinagh(d.text_tachelhit or ""),
                # i les altres maneres de dir-ho, cadascuna amb qui la diu i d'on és
                "variants": [v for v in said.get(d.id, []) if _another_way(v["text"], d.text_tachelhit)]}

    # per unitat de gramàtica, que és com es llegeix un capítol: una cosa després de l'altra
    sections = []
    used = set()
    for g in c["grammar"]:
        here = [d for d in rows if g in grammar_course.parse(d.grammar)]
        used.update(d.id for d in here)
        sections.append({"slug": g, "title": titles.get(g, g),
                         "sentences": [card(d) for d in here[:8]], "total": len(here),
                         "with_voice": sum(1 for d in here if d.audio_url)})
    rest = [d for d in rows if d.id not in used]

    out = {
        "n": c["n"], "slug": c["slug"], "name": c["name"], "title": c["title"],
        "about": c["about"], "functions": c["functions"], "roles": c["roles"],
        "cover": artwork(db, "method").get(c["slug"]),
        # El text del capítol, amb les NOSTRES frases repartides per dins.
        #
        # No és el llibre traduït i, a part, un munt de frases nostres al final: cada secció
        # ensenya el que explica i tot seguit com ho diu la gent que coneixem, amb la seva veu i
        # la seva imatge. El llibre hi posa el recorregut; la biblioteca, les persones.
        "content": method_mod.content_with_ours(db, c["slug"], rows, card),
        "topics": [{"slug": t, "label": labels.get(t, t)} for t in c["topics"]],
        "sections": sections,
        "also": [card(d) for d in rest[:12]],
        "sentences": len(rows),
        "with_voice": sum(1 for d in rows if d.audio_url),
        **method_mod.readiness(c, rows),
        "missing": method_mod.what_is_missing(c, rows),
        "source": method_mod.SOURCE,
        # La sortida del capítol: la pràctica que en comprova les funcions. Fins ara un capítol
        # s'acabava i no tornava mai; una pràctica, en canvi, puntua cada frase i el repàs
        # espaiat les fa tornar soles.
        "practice_test": next(({"id": t.id, "title": t.title, "steps": len(practice_steps.steps_of(db, t.id))}
                          for t in db.query(TestModel).filter(
                              TestModel.title.ilike(f"%Capítol {c['n']} ·%")).all()), None),
    }
    _CHAPTER_CACHE[slug] = (mark, out)
    return out


@app.post("/method/{slug}/line")
def method_line_drill(slug: str,
                      kind: str = Body(..., embed=True),
                      index: int = Body(..., embed=True),
                      section: Optional[str] = Body(None, embed=True),
                      db: Session = Depends(get_db),
                      user: UserModel = Depends(require_user)):
    """La frase nostra que hi ha darrere una línia d'un capítol, creant-la el primer cop.

    El Mètode no estarà acabat fins que les seves línies es puguin escoltar, i una línia del
    manual no és encara una frase de la biblioteca: és text dins del capítol. Perquè algú la pugui
    gravar, ha de ser un drill.

    Això no és paperassa: **gravar una línia del llibre la converteix en una frase nostra**, i
    aquell és el camí pel qual un capítol adaptat del Souss es torna una recollida de l'Atles.
    Qualsevol que tingui nom pot fer-ho; el que no pot fer qualsevol és canviar el TEXT del
    capítol, que segueix sent de qui administra.
    """
    if kind not in method_mod.LINE_KINDS:
        raise HTTPException(status_code=400, detail=f"kind ha de ser un de {method_mod.LINE_KINDS}")
    if not method_mod.chapter(slug):
        raise HTTPException(status_code=404, detail="Aquest capítol no existeix")
    try:
        out = method_mod.drill_for_line(db, slug, kind, section, int(index), user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    d = db.query(DrillModel).filter(DrillModel.id == out["drill_id"]).first()
    return {**out, "drill": Drill.model_validate(d, from_attributes=True)}


@app.put("/method/{slug}/content")
def put_method_content(slug: str, body: dict = Body(...),
                       db: Session = Depends(get_db),
                       user: UserModel = Depends(require_admin)):
    """Desa el text d'un capítol: l'explicació, el diàleg i el vocabulari.

    Viu a la base de dades i no al repositori (vegeu `models.MethodChapter`), i per això es
    corregeix des d'aquí: qui administra pot arreglar una frase sense desplegar res.
    """
    try:
        saved = method_mod.store_content(db, slug, body, who=(user.display_name or user.username))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"slug": slug, "ok": True, "sections": len(saved.get("sections") or [])}


@app.get("/practice/collections")
def practice_collections(db: Session = Depends(get_db),
                         user: Optional[UserModel] = Depends(get_current_user)):
    """How the library is offered for practice: by recording day (our speakers' sessions), by
    subject, by grammar unit, and the hand-made lists. The lists are the asking person's own."""
    return practice_mod.collections(db, user)


@app.get("/practice/session")
def practice_session(day: Optional[str] = None, speaker: Optional[str] = None, topic: Optional[str] = None,
                     unit: Optional[str] = None, test_id: Optional[int] = None, ids: Optional[str] = None,
                     video: Optional[str] = None, person: Optional[str] = None, tag: Optional[str] = None,
                     with_voice: bool = True, limit: int = 10, offset: int = 0, db: Session = Depends(get_db)):
    """The drills of one practice session (real sentences with a voice, recorded and pictured first;
    `ids` = an explicit list, e.g. the drills due for review) and, per drill, the card data:
    speaker, hard sounds, pronunciation tips."""
    only = [int(x) for x in ids.split(",") if x.strip().isdigit()] if ids else None
    rows = practice_mod.session_rows(db, day=day, speaker=speaker, topic=topic, unit=unit, test_id=test_id, ids=only,
                                     video=video, person=person, tag=tag, with_voice=with_voice, limit=limit, offset=offset)
    return {"drills": [Drill.model_validate(d, from_attributes=True) for d in rows], "cards": [practice_mod.card(d) for d in rows]}


@app.get("/grammar")
def grammar_units():
    """The course: units in order with, per unit, how many drills illustrate it."""
    return {"units": [{k: u[k] for k in ("slug", "title", "level")} for u in grammar_course.UNITS],
            "counts": grammar_course.counts(SessionLocal), "status": grammar_course.status()}


def _write_missing_notes() -> None:
    """Explain each unit's own examples: for every sentence a unit can quote, what that sentence
    shows of that unit's point. Resumable, so a restart carries on where it stopped; the lessons
    are written first because a page can wait for a note but not for a lesson."""
    import time
    time.sleep(240)  # the lessons go first, then this works through the library quietly
    if not gemini_available():
        print("[NOTES] skipped: no Gemini key")
        return
    try:
        grammar_course.fill_notes(SessionLocal, _grammar_unit_rows, _load_grammar())
    except Exception as e:
        print(f"[NOTES] stopped: {e}")


def _write_missing_lessons() -> None:
    """Write the lessons that are missing or outdated, oldest unit of the course first. One at a
    time: Gemini is slow and the free database has few connections."""
    import time
    time.sleep(20)  # let the server answer its first requests first
    if not gemini_available():
        print("[GRAMMAR] self-write skipped: no Gemini key")
        return
    written = 0
    for unit in grammar_course.UNITS:
        slug = unit["slug"]
        try:
            with SessionLocal() as db:
                rows = _grammar_unit_rows(db, slug)
                if not rows:
                    continue
                examples = grammar_course.pick_examples(rows, slug=slug)
                before = grammar_course.get_lesson(db, slug, "", examples, unit_ids={d.id for d in rows})
                if not before.get("writing") and not before.get("stale"):
                    continue
        except Exception as e:
            print(f"[GRAMMAR] self-write {slug}: {e}")
            continue
        try:
            with SessionLocal() as db:
                rows = _grammar_unit_rows(db, slug)
                examples = grammar_course.pick_examples(rows, slug=slug)
                lesson = grammar_course.write_lesson(slug, _load_grammar(), examples,
                                                     sheet=grammar_course.sheet_for(db, slug, _load_grammar()),
                                                     tables=grammar_course.paradigms(rows),
                                                     notes=grammar_course.notes_for(db, slug))
                lesson["unit_size"] = len({d.id for d in rows})
                grammar_course._store_lesson(db, slug, lesson)
                written += 1
                print(f"[GRAMMAR] self-write {slug}: {len(lesson.get('steps') or [])} steps")
        except Exception as e:
            print(f"[GRAMMAR] self-write {slug}: {e}")
        time.sleep(5)
    print(f"[GRAMMAR] self-write finished: {written} lesson(s)")


def _grammar_unit_rows(db, slug: str, limit: int = 1500):
    """The unit's drills, pictured-and-voiced first, then voiced, then by id; excluded tags left out."""
    if slug == grammar_course.SOUNDS_UNIT:
        return grammar_course.sound_rows(db, limit=min(limit, 300))
    q = grammar_course.not_excluded(db.query(DrillModel).filter(DrillModel.grammar.ilike(f"%{slug}%")), DrillModel)
    rows = q.order_by(DrillModel.audio_url.isnot(None).desc(), DrillModel.image_url.isnot(None).desc(), DrillModel.id.asc()).limit(limit).all()
    return [d for d in rows if slug in grammar_course.parse(d.grammar)]


def _grammar_unit_payload(db, slug: str, limit: int, force: bool, deep: bool = False):
    unit = next((u for u in grammar_course.UNITS if u["slug"] == slug), None)
    if unit is None:
        raise HTTPException(status_code=404, detail="Unit not found")
    rows = _grammar_unit_rows(db, slug)
    examples = grammar_course.pick_examples(rows, slug=slug)
    practice = grammar_course.practice_rows(rows, slug=slug)  # the test: sentences (and words, in the units about words)
    try:
        lesson = grammar_course.get_lesson(db, slug, _load_grammar() if gemini_available() else "", examples, force=force,
                                           unit_ids={d.id for d in rows}, session_factory=SessionLocal,
                                           tables=grammar_course.paradigms(rows), deep=deep)
    except Exception as e:
        print(f"[GRAMMAR] lesson {slug}: {e}")
        lesson = {"intro": "", "steps": [{"type": "explain", "title": unit["title"], "text": "La lliçó encara no s’ha pogut escriure. Mira els exemples de la biblioteca mentrestant.", "examples": examples[:3]}, {"type": "end"}], "error": str(e)[:160]}
    # La tifinagh de cada so citat, al títol i al text. S'hi posa en SERVIR la lliçó i no en
    # escriure-la, perquè les que ja hi ha escrites també l'han de portar: no es poden reescriure
    # —el compte de Gemini és sense crèdit— i l'amo ho va demanar per a tot arreu.
    for step in (lesson.get("steps") or []):
        for field in ("title", "text", "question"):
            if isinstance(step.get(field), str):
                step[field] = grammar_course.with_letters(step[field])
    if isinstance(lesson.get("intro"), str):
        lesson["intro"] = grammar_course.with_letters(lesson["intro"])

    # Les altres maneres de dir cada frase citada. La lliçó es va escriure un dia i es desa tal
    # com va quedar; això s'hi afegeix en SERVIR-LA, perquè una veu gravada avui s'ha de veure
    # avui i no quan es torni a escriure la lliçó.
    said = other_ways(db)
    if said:
        for step in (lesson.get("steps") or []):
            for e in (step.get("examples") or []):
                e["variants"] = [v for v in said.get(e.get("id"), []) if _another_way(v["text"], e.get("shi"))]
            if step.get("example"):
                step["example"]["variants"] = [v for v in said.get(step["example"].get("id"), [])
                                               if _another_way(v["text"], step["example"].get("shi"))]
    total = len(rows)  # the rows are already every drill of the unit (the query's limit is far above any unit)
    return {**{k: unit[k] for k in ("slug", "title", "level")}, "lesson": lesson, "total": total,
            "practice": [d.id for d in practice],
            "drills": [Drill.model_validate(d, from_attributes=True) for d in rows[:max(1, min(limit, 300))]]}


def _lesson_quotes(db, slug: str) -> set:
    """The drills the unit's stored lesson quotes, if it has one."""
    from models import GrammarLesson
    row = db.query(GrammarLesson).filter(GrammarLesson.id == slug).first()
    if row is None:
        return set()
    try:
        return grammar_course.quoted_ids(json.loads(row.body))
    except Exception:
        return set()


@app.get("/grammar/wishlist")
def grammar_wishlist(per_unit: int = 8, db: Session = Depends(get_db)):
    """What our own speakers (Aït Mraw) could record next: for each unit, how many of its sentences
    already carry an Aït Mraw voice and the sentences from elsewhere worth recording in their words
    (real sentences, pictured first, none that already has an Aït Mraw take). Units with the fewest
    Aït Mraw voices first."""
    mraw_takes = {r[0] for r in db.query(RecordingModel.drill_id).filter(
        (RecordingModel.region.ilike("%mraw%")) | (RecordingModel.speaker.in_(("Halima", "Driss")))).all()}
    out = []
    for unit in grammar_course.UNITS:
        rows = _grammar_unit_rows(db, unit["slug"])
        in_lesson = _lesson_quotes(db, unit["slug"])  # what the unit's lesson shows a learner
        voiced = sum(1 for d in rows if (grammar_course.origin(d) == grammar_course.AIT_MRAW and d.audio_url) or d.id in mraw_takes)
        wanted = [d for d in grammar_course.practice_rows(rows, limit=10000, slug=unit["slug"])
                  if len(d.text_tachelhit or "") <= 90
                  and (getattr(d, "voice_wanted", False)  # somebody asked for this one by hand
                       or (grammar_course.origin(d) != grammar_course.AIT_MRAW and d.id not in mraw_takes))]
        # what a person asked for first, then the sentences the lesson quotes (recording those
        # changes what a learner hears), then the Beni Mellal deck, then pictured, then voiced
        wanted.sort(key=lambda d: (not getattr(d, "voice_wanted", False), d.id not in in_lesson,
                                   grammar_course.origin(d) != "Beni Mellal",
                                   not d.image_url, not d.audio_url, d.id))
        out.append({**{k: unit[k] for k in ("slug", "title", "level")}, "total": len(rows), "aitmraw_voiced": voiced,
                    "in_lesson": sum(1 for d in wanted if d.id in in_lesson),
                    "asked": sum(1 for d in wanted if getattr(d, "voice_wanted", False)),
                    "wanted": [Drill.model_validate(d, from_attributes=True) for d in wanted[:max(0, min(per_unit, 30))]]})
    out.sort(key=lambda u: (u["aitmraw_voiced"], -u["total"]))
    return {"units": out}


@app.get("/grammar/{slug}/lesson")
def grammar_lesson(slug: str, db: Session = Depends(get_db)):
    """Just the unit's lesson: what a page asks for again while a new one is being written."""
    rows = _grammar_unit_rows(db, slug)
    examples = grammar_course.pick_examples(rows, slug=slug)
    lesson = grammar_course.get_lesson(db, slug, _load_grammar() if gemini_available() else "", examples,
                                       unit_ids={d.id for d in rows}, session_factory=SessionLocal,
                                       tables=grammar_course.paradigms(rows))
    from models import GrammarLesson
    row = db.query(GrammarLesson).filter(GrammarLesson.id == slug).first()
    return {"slug": slug, "lesson": lesson, "writing": slug in grammar_course.writing(),
            "hand_written": bool(row is not None and getattr(row, "hand_written", False))}


@app.put("/grammar/{slug}/lesson")
def put_grammar_lesson(slug: str, lesson: Dict[str, Any] = Body(..., embed=True),
                       db: Session = Depends(get_db), _admin: UserModel = Depends(require_admin)):
    """Write a unit's lesson by hand (#187). From now on the writer leaves it alone.

    A lesson is `{"intro": str, "steps": [...]}`. Steps must be the kinds the course knows how to
    show, because a step nobody can draw is a blank page for whoever is learning.
    """
    from models import GrammarLesson
    steps = lesson.get("steps")
    if not isinstance(steps, list) or not steps:
        raise HTTPException(status_code=400, detail="Una lliçó necessita com a mínim un pas")
    allowed = {"explain", "pattern", "quiz", "tip", "dialect", "end"}
    for i, step in enumerate(steps):
        if not isinstance(step, dict) or step.get("type") not in allowed:
            raise HTTPException(status_code=400,
                                detail=f"El pas {i + 1} no és d'un tipus que el curs sàpiga ensenyar")
        if step.get("type") == "quiz":
            options = step.get("options")
            if not isinstance(options, list) or len(options) < 2:
                raise HTTPException(status_code=400, detail=f"La pregunta del pas {i + 1} no té respostes")
            if not isinstance(step.get("answer"), int) or not (0 <= step["answer"] < len(options)):
                raise HTTPException(status_code=400, detail=f"La pregunta del pas {i + 1} no diu quina és la bona")

    body = json.dumps({k: v for k, v in lesson.items() if k not in ("writing", "stale")},
                      ensure_ascii=False)
    row = db.query(GrammarLesson).filter(GrammarLesson.id == slug).first()
    if row is None:
        row = GrammarLesson(id=slug, body=body, version=grammar_course.LESSON_VERSION)
        db.add(row)
    row.body = body
    row.version = grammar_course.LESSON_VERSION
    row.hand_written = True
    row.updated_at = datetime.utcnow()
    db.commit()
    return {"slug": slug, "hand_written": True, "steps": len(steps)}


@app.post("/grammar/{slug}/row")
def grammar_row_drill(slug: str,
                      step: int = Body(..., embed=True),
                      row: int = Body(..., embed=True),
                      deep: bool = Body(False, embed=True),
                      db: Session = Depends(get_db),
                      user: UserModel = Depends(require_user)):
    """La frase de la biblioteca darrere una fila d'una taula de formes, creant-la el primer cop.

    Una taula de formes és on la gramàtica es veu d'un cop d'ull, i era l'únic lloc de la lliçó
    que no es podia dir. Gravar-ne una fila la converteix en una frase nostra, igual que al
    Mètode: qualsevol que tingui nom pot fer-ho.
    """
    try:
        out = grammar_course.drill_for_row(db, slug, int(step), int(row), user, deep=deep)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    d = db.query(DrillModel).filter(DrillModel.id == out["drill_id"]).first()
    return {**out, "drill": Drill.model_validate(d, from_attributes=True)}


@app.post("/grammar/{slug}/lesson/release")
def release_grammar_lesson(slug: str, db: Session = Depends(get_db),
                           _admin: UserModel = Depends(require_admin)):
    """Hand a hand-written lesson back to the writer: the next open writes it again (#187)."""
    from models import GrammarLesson
    row = db.query(GrammarLesson).filter(GrammarLesson.id == slug).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Aquesta unitat no té cap lliçó desada")
    row.hand_written = False
    db.commit()
    return {"slug": slug, "hand_written": False}


@app.get("/grammar/{slug}")
def grammar_unit(slug: str, limit: int = 60, db: Session = Depends(get_db)):
    """One unit: its lesson (steps with the library's own examples, written once and kept in the
    database) and its drills, the pictured-and-voiced ones first."""
    return _grammar_unit_payload(db, slug, limit, force=False)


@app.post("/grammar/run")
def grammar_run(force: bool = False, limit: int = 4000, ids: Optional[str] = None, _admin: UserModel = Depends(require_admin)):
    """Admin: classify drills into grammar units in the background (all auto ones with force)."""
    only = [int(x) for x in ids.split(",") if x.strip().isdigit()] if ids else None
    if grammar_course.status()["running"]:
        return {"started": False, "reason": "already running", **grammar_course.status()}
    threading.Thread(target=grammar_course.run, args=(SessionLocal, force, limit, only), daemon=True).start()
    return {"started": True}


@app.get("/grammar/{slug}/deep")
def grammar_deep(slug: str, limit: int = 60, db: Session = Depends(get_db)):
    """The unit's «a fons» level: the same unit taken further, with the sentences the first lesson
    does not use. Written the first time somebody opens it; the page polls while it is written."""
    return _grammar_unit_payload(db, slug, limit, force=False, deep=True)


@app.post("/grammar/{slug}/deep/rewrite")
def grammar_deep_rewrite(slug: str, limit: int = 60, db: Session = Depends(get_db),
                         _admin: UserModel = Depends(require_admin)):
    """Admin: write the unit's «a fons» level again."""
    return _grammar_unit_payload(db, slug, limit, force=True, deep=True)


@app.get("/grammar/notes/status")
def grammar_notes_status():
    """How far the «why this sentence is here» pass has got."""
    return grammar_course.notes_status()


@app.post("/grammar/notes/run")
def grammar_notes_run(slug: Optional[str] = None, _admin: UserModel = Depends(require_admin)):
    """Admin: explain the sentences of one unit, or of the whole course, in the background."""
    if grammar_course.notes_status()["running"]:
        return {"started": False, "reason": "already running", **grammar_course.notes_status()}
    threading.Thread(target=grammar_course.fill_notes,
                     args=(SessionLocal, _grammar_unit_rows, _load_grammar(), slug), daemon=True).start()
    return {"started": True}


@app.post("/grammar/{slug}/rewrite")
def grammar_rewrite(slug: str, limit: int = 60, db: Session = Depends(get_db), _admin: UserModel = Depends(require_admin)):
    """Admin: write the unit's lesson again (after a change in the course, the examples or the compendium)."""
    return _grammar_unit_payload(db, slug, limit, force=True)


@app.get("/lexicon/status")
def lexicon_status():
    """Dictionary + conjugation tables used to ground the tutor (loaded on first use)."""
    return lexicon.status()


@app.get("/lexicon/lookup")
def lexicon_lookup(q: str = ""):
    """Dictionary entries and conjugation hits for the words of `q` (Latin or Tifinagh)."""
    if not lexicon.status()["loaded"]:
        lexicon.load()
    return {"query": q, "hits": lexicon.lookup(q), "attribution": lexicon.ATTRIBUTION}


def _ai_actor(request: Request, user: Optional[UserModel]) -> str:
    if user is not None:
        return f"user:{user.id}"
    host = (request.client.host if request.client else "") or request.headers.get("x-forwarded-for", "")
    return "ip:" + hashlib.sha256(host.split(",")[0].strip().encode("utf-8")).hexdigest()[:16]


def _ai_gate(feature: str):
    """Dependency for the interactive AI endpoints: Gemini configured, the month's budget not
    spent, the person's daily cap not reached; tags the call for the meter. Async on purpose:
    the context it sets must be the request's own, so the sync endpoint (run in a thread
    copy of it) and the Gemini hook see the feature + actor."""
    async def dep(request: Request, user: Optional[UserModel] = Depends(get_current_user)) -> Dict[str, Any]:
        if not gemini_available():
            raise HTTPException(status_code=503, detail="AI assistant not configured (GEMINI_API_KEY missing)")
        actor = _ai_actor(request, user)
        try:
            info = await run_in_threadpool(ai_meter.check_person, actor, bool(user and user.is_admin), user is None)
        except BudgetExceeded as e:
            raise HTTPException(status_code=429, detail=str(e))
        ai_budget.set_context(feature, actor)
        return info
    return dep


@app.get("/ai/usage")
def ai_usage(request: Request, user: Optional[UserModel] = Depends(get_current_user)):
    """What the caller has used today (and their cap) and how much of the monthly budget
    is spent; admins also get the month's spend by feature."""
    return ai_meter.summary(_ai_actor(request, user), bool(user and user.is_admin), user is None)


@app.get("/ai/status")
def ai_status():
    """Whether the AI agent is configured (and within budget), and the grammar corpus size."""
    return {"available": gemini_available() and ai_meter.budget_ok(), "configured": gemini_available(),
            "budget_ok": ai_meter.budget_ok(), "budget_eur": ai_budget.monthly_budget_eur(),
            "grammar_chars": len(_load_grammar())}

@app.post("/ai/ask")
def ai_ask(
    question: str = Body(..., embed=True),
    drill_id: Optional[int] = Body(None, embed=True),
    history: Optional[List[Dict]] = Body(None, embed=True),
    db: Session = Depends(get_db),
    _gate: Dict[str, Any] = Depends(_ai_gate("ask")),
):
    """
    Ask the grammar tutor. Grounded in the Amazigh grammar compendium; can use
    a selected drill's content and prior conversation turns as context.
    history: [{"role": "user"|"model", "text": "..."}] (most recent last).
    """
    if not gemini_available():
        raise HTTPException(status_code=503, detail="AI assistant not configured (GEMINI_API_KEY missing)")
    if not (question or "").strip():
        raise HTTPException(status_code=400, detail="Empty question")

    system_instruction = _build_system_instruction(db)

    contents = []
    for turn in (history or [])[-8:]:  # keep the last few turns for context
        contents.append({"role": turn.get("role", "user"), "text": turn.get("text", "")})

    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first() if drill_id else None
    user_text = question.strip()
    ctx = _drill_context(drill)
    if ctx:
        user_text = f"{ctx}\n\nPREGUNTA: {question.strip()}"
    contents.append({"role": "user", "text": user_text})

    try:
        answer = gemini_generate(system_instruction, contents, max_output_tokens=1200)
        return {"answer": answer, "used_drill": bool(drill)}
    except BudgetExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        print(f"[AI] ask failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI assistant error: {str(e)[:200]}")

@app.post("/ai/analyze-drill/{drill_id}")
def ai_analyze_drill(drill_id: int, db: Session = Depends(get_db), _gate: Dict[str, Any] = Depends(_ai_gate("analyze"))):
    """
    Morphological/grammatical analysis of the ATTESTED Tachelhit form the user
    collected in this drill — grounded in the grammar and the learner's own
    corpus. This is documentation, not correction: it explains the form as it
    is, and notes how it differs from the standard.
    """
    if not gemini_available():
        raise HTTPException(status_code=503, detail="AI assistant not configured (GEMINI_API_KEY missing)")
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
    if not (drill.text_tachelhit or "").strip():
        raise HTTPException(status_code=400, detail="Aquest drill no té text en taixelhit per analitzar")

    prompt = (
        _drill_context(drill) + "\n\n"
        "Analitza la forma en taixelhit ATTESTADA d'aquest drill (és una dada de camp d'un parlant real). "
        "Estructura la resposta així:\n"
        "1. **Transcripció i lectura** (tifinag + llatí, pronunciació aproximada).\n"
        "2. **Anàlisi morfològica**: arrel, tema, aspecte verbal si és verb (aorist/perfectiu/imperfectiu), "
        "estat (lliure/annexió) i marques de gènere/nombre si és nom, pronoms/afixos, etc. Cita seccions del compendi (§).\n"
        "3. **Sintaxi i significat**: com es construeix i què vol dir, amb el paral·lel català.\n"
        "4. **Variació**: si la forma difereix de l'estàndard IRCAM o del taixelhit del Sus, indica-ho SENSE corregir-la "
        "(la forma recollida és correcta per a la seva varietat).\n"
        "Sigues concís i pedagògic."
    )
    try:
        analysis = gemini_generate(_build_system_instruction(db),
                                   [{"role": "user", "text": prompt}], max_output_tokens=1400)
        return {"drill_id": drill_id, "analysis": analysis}
    except BudgetExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        print(f"[AI] analyze-drill failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI assistant error: {str(e)[:200]}")

_WORD_RE = re.compile(r"[^\W\d_]{3,}", re.UNICODE)
_EXPLAIN_STOP = {"the", "and", "que", "per", "amb", "una", "els", "les", "del", "dels", "est", "ara"}


def _drill_words(d) -> set:
    """Content words of a drill's Tachelhit (speaker text, Latin reading, or the machine
    draft without its [? ...] bracket), lowercased, for the 'drills with the same words' list."""
    text = " ".join(x for x in (d.text_tachelhit, d.text_tachelhit_latin, d.text_tachelhit_suggested) if x)
    text = text.replace("[?", " ").replace("[", " ").replace("]", " ").replace("|", " ")
    return {w.lower() for w in _WORD_RE.findall(text)} - _EXPLAIN_STOP


def _related_drills(drill, db, limit: int = 8) -> list:
    words = _drill_words(drill)
    if not words:
        return []
    out = []
    for d in db.query(DrillModel).filter(DrillModel.id != drill.id).all():
        shared = words & _drill_words(d)
        if shared:
            out.append((len(shared), d, sorted(shared)))
    out.sort(key=lambda x: (-x[0], x[1].id))
    return [{"id": d.id, "text_catalan": d.text_catalan,
             "text": d.text_tachelhit or d.text_tachelhit_latin or d.text_tachelhit_suggested,
             "words": shared,
             # playable in place: the speaker's voice, else the synthetic one; and the picture for the card
             "audio_url": normalize_media_url(d.audio_url) if d.audio_url else None,
             "audio_tts_shi_url": normalize_media_url(d.audio_tts_shi_url) if d.audio_tts_shi_url else None,
             "image_url": d.image_url, "region": d.region} for _, d, shared in out[:limit]]


@app.post("/ai/explain/{drill_id}")
def ai_explain_drill(drill_id: int, db: Session = Depends(get_db), _gate: Dict[str, Any] = Depends(_ai_gate("explain"))):
    """
    Learner's explanation of a drill: the Tachelhit phrase word by word, which Catalan
    word each one answers to, what is not said literally — plus the other drills in the
    corpus that use the same words. Works on the speaker's text or, failing that, on the
    machine draft (said so to the learner).
    """
    if not gemini_available():
        raise HTTPException(status_code=503, detail="AI assistant not configured (GEMINI_API_KEY missing)")
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
    text = (drill.text_tachelhit or "").strip()
    draft = (drill.text_tachelhit_suggested or drill.text_tachelhit_latin or "").strip()
    # the machine draft carries a "[? ... | alt]" uncertainty bracket: not part of the sentence
    draft = re.sub(r"\s+", " ", draft.replace("[?", " ").replace("[", " ").replace("]", " ").replace("|", " / ")).strip()
    if not text and not draft:
        raise HTTPException(status_code=400, detail="Aquest drill encara no té cap lectura en taixelhit per explicar")
    if not text and draft and draft_status(getattr(drill, "draft_check", None), drill.text_tachelhit_suggested) == "no":
        raise HTTPException(status_code=400, detail="La lectura automàtica d'aquest drill no quadra amb el significat: cal la transcripció d'un parlant abans d'explicar-la")
    source_note = ("" if text else
                   "ATENCIÓ: no hi ha text confirmat pel parlant; la lectura és un ESBORRANY automàtic "
                   f"(«{draft}»). Explica'l igualment però digues-ho a l'aprenent en una línia. Per a CADA paraula digues si és una "
                   "paraula amaziga coneguda (i quina) o una lectura dubtosa de la màquina; no inventis arrels ni morfologia per fer "
                   "quadrar l'esborrany amb el català, i si la frase sencera no quadra amb el significat, digues-ho clarament.")
    prompt = (
        _drill_context(drill) + ("\n- Esborrany automàtic: " + draft if not text and draft else "") + "\n\n"
        + source_note + "\n\n"
        "Explica aquesta frase a un aprenent de taixelhit que parla català. Si el context porta entrades de DICCIONARI I "
        "CONJUGACIONS, basa-t'hi: són la font fiable per al significat de cada paraula i per al temps verbal (les «coincidències aproximades» només si quadren amb el significat); digues entre "
        "parèntesis [Oulhaj] o [IRCAM] quan les facis servir. Format, en català, sense preàmbuls:\n"
        "1. **Paraula per paraula**: una línia per cada paraula taixelhit, així: `paraula` — significat — a quina paraula catalana respon "
        "(o «no hi és literalment»). Si una paraula catalana de la traducció no té paraula pròpia en taixelhit, digues com s'expressa.\n"
        "2. **Com està construïda**: dues o tres frases (verb i aspecte, pronoms o afixos, ordre).\n"
        "3. **Per recordar-la**: una pista breu (una paraula arrel que surt en altres frases, un paral·lel).\n"
        "Cita el compendi (§) només si cal. Màxim 220 paraules."
    )
    try:
        explanation = gemini_generate(_build_system_instruction(db),
                                      [{"role": "user", "text": prompt}], max_output_tokens=1200)
    except BudgetExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        print(f"[AI] explain failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI assistant error: {str(e)[:200]}")
    return {"drill_id": drill_id, "explanation": explanation, "draft": not text,
            "related": _related_drills(drill, db)}


@app.post("/ai/suggest-translation/{drill_id}")
def ai_suggest_translation(drill_id: int, db: Session = Depends(get_db), _gate: Dict[str, Any] = Depends(_ai_gate("suggest"))):
    """
    Generate an AI *draft* Tachelhit form from the drill's Catalan (or a Catalan
    draft from the Tachelhit) and store it in the *_suggested column — never in
    the human-attested gold field. The learner reviews and, if right, accepts it.
    """
    if not gemini_available():
        raise HTTPException(status_code=503, detail="AI assistant not configured (GEMINI_API_KEY missing)")
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")

    if (drill.text_catalan or "").strip():
        direction, target_field = "del català al taixelhit", "text_tachelhit_suggested"
        source = drill.text_catalan
    elif (drill.text_tachelhit or "").strip():
        direction, target_field = "del taixelhit al català", "text_catalan_suggested"
        source = drill.text_tachelhit
    else:
        raise HTTPException(status_code=400, detail="El drill necessita text en català o taixelhit")

    prompt = (
        f"Tradueix {direction} el següent, tenint en compte la varietat documentada. "
        f"Respon NOMÉS amb la traducció, sense explicacions ni cometes:\n\n{source}"
    )
    try:
        suggestion = gemini_generate(_build_system_instruction(db),
                                     [{"role": "user", "text": prompt}], max_output_tokens=200).strip()
        setattr(drill, target_field, suggestion)
        db.commit()
        return {"drill_id": drill_id, "field": target_field, "suggestion": suggestion}
    except BudgetExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        print(f"[AI] suggest-translation failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI assistant error: {str(e)[:200]}")

AGENT_TOOLS = [
    {
        "name": "create_drill",
        "description": "Crea un drill nou. Omple els camps que sàpigues; deixa buits els que no.",
        "parameters": {"type": "object", "properties": {
            "text_catalan": {"type": "string"},
            "text_tachelhit": {"type": "string", "description": "forma en taixelhit (tifinag o llatí)"},
            "text_tachelhit_latin": {"type": "string"},
            "text_arabic": {"type": "string"},
            "variety": {"type": "string"},
            "region": {"type": "string"},
            "tag": {"type": "string"},
        }},
    },
    {
        "name": "update_drill",
        "description": "Modifica camps d'un drill existent pel seu id. Envia només els camps a canviar.",
        "parameters": {"type": "object", "properties": {
            "drill_id": {"type": "integer"},
            "text_catalan": {"type": "string"},
            "text_tachelhit": {"type": "string"},
            "text_tachelhit_latin": {"type": "string"},
            "text_arabic": {"type": "string"},
            "variety": {"type": "string"},
            "region": {"type": "string"},
            "tag": {"type": "string"},
        }, "required": ["drill_id"]},
    },
    {
        "name": "search_drills",
        "description": "Cerca drills al corpus per text (qualsevol llengua) o etiqueta. Retorna coincidències.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
        }, "required": ["query"]},
    },
    {
        "name": "what_can_a_practice_be_about",
        "description": ("Què pot oferir la biblioteca per a una pràctica: unitats de gramàtica, temes, "
                        "qui parla, dies de gravació i etiquetes, amb quantes frases té cadascun. "
                        "Crida-la abans de triar frases si no saps què hi ha."),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "find_sentences_for_practice",
        "description": ("Frases que es poden posar en una pràctica. Només en torna de SENCERES: amb veu, "
                        "amb el text amazic escrit i amb el significat en català. Van de més curta a més "
                        "llarga, que és l'ordre en què s'aprenen. Filtra per text lliure o per una "
                        "col·lecció (unit, topic, person, tag, day)."),
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "text lliure, en qualsevol de les llengües"},
            "unit": {"type": "string", "description": "slug d'una unitat de gramàtica"},
            "topic": {"type": "string", "description": "slug d'un tema"},
            "person": {"type": "string", "description": "qui parla, p. ex. Halima"},
            "tag": {"type": "string"},
            "limit": {"type": "integer"},
        }},
    },
    {
        "name": "add_to_practice",
        "description": ("Afegeix passos al FINAL d'una pr\u00e0ctica, sense tocar els que ja hi s\u00f3n. \u00c9s el que "
                        "vols quan et demanen \u00abafegeix-hi m\u00e9s frases\u00bb: build_practice substitueix tota "
                        "la seq\u00fc\u00e8ncia i nom\u00e9s s'ha de fer servir per refer-la de cap i de nou."),
        "parameters": {"type": "object", "properties": {
            "test_id": {"type": "integer"},
            "steps": {"type": "array", "description": "els passos nous, en ordre", "items": {
                "type": "object", "properties": {
                    "kind": {"type": "string"},
                    "drill_id": {"type": "integer"},
                    "heading": {"type": "string", "description": "nom\u00e9s per a kind=note"},
                    "text": {"type": "string", "description": "nom\u00e9s per a kind=note"},
                }, "required": ["kind"]}},
        }, "required": ["test_id", "steps"]},
    },
    {
        "name": "illustrate_sentence",
        "description": ("Dibuixa una imatge per a una frase que no en t\u00e9, amb l'estil de les targetes. "
                        "Serveix quan et demanen \u00abafegeix-hi imatges\u00bb: les imatges van a les FRASES, no "
                        "als passos, i aix\u00ed les t\u00e9 tothom qui les faci servir. Una frase que ja en t\u00e9 "
                        "no es toca."),
        "parameters": {"type": "object", "properties": {
            "drill_id": {"type": "integer"},
            "hint": {"type": "string", "description": "qu\u00e8 s'hi ha de veure, si vols guiar-ho"},
        }, "required": ["drill_id"]},
    },
    {
        "name": "read_practice",
        "description": "Què té ara mateix una pràctica: el seu nom i els seus passos en ordre.",
        "parameters": {"type": "object", "properties": {
            "test_id": {"type": "integer"},
        }, "required": ["test_id"]},
    },
    {
        "name": "build_practice",
        "description": ("Escriu la seqüència d'una pràctica, substituint la que hi hagi. Cada pas té una "
                        "eina (kind) i, si l'eina demana una frase, el seu drill_id. Eines: listen_pick "
                        "(escolta i tria), write_heard (escolta i escriu), say_it (digues-ho i compara't), "
                        "look_say (mira la imatge i digues-ho), fill_gap (omple el buit), word_by_word, "
                        "script_swap (tifinag o llatí), pick_spelling, i note (una explicació, sense "
                        "frase: posa-li heading i text). Comença amb una nota que digui què s'hi aprèn, "
                        "i no repeteixis sempre la mateixa eina."),
        "parameters": {"type": "object", "properties": {
            "test_id": {"type": "integer"},
            "steps": {"type": "array", "description": "els passos, en ordre", "items": {
                "type": "object", "properties": {
                    "kind": {"type": "string"},
                    "drill_id": {"type": "integer"},
                    "heading": {"type": "string", "description": "només per a kind=note"},
                    "text": {"type": "string", "description": "només per a kind=note"},
                }, "required": ["kind"]}},
        }, "required": ["test_id", "steps"]},
    },
    {
        "name": "speak_tachelhit",
        "description": "Sintetitza veu en taixelhit d'un text perquè l'usuari el pugui escoltar. Retorna una URL d'àudio.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string"},
        }, "required": ["text"]},
    },
]

def _agent_executor(db, user=None):
    """Return a function(name, args)->dict that runs the agent's tool calls.

    `user` is whoever is talking to the copilot. It matters for the tools that write a practice:
    a copilot is not a way around permissions."""
    ALLOWED = {"text_catalan", "text_tachelhit", "text_tachelhit_latin", "text_arabic", "variety", "region", "tag"}

    def run(name, args):
        if name == "create_drill":
            data = {k: v for k, v in (args or {}).items() if k in ALLOWED and v}
            if not data:
                return {"error": "cap camp per crear el drill"}
            d = DrillModel(**data, author="AI Copilot")
            db.add(d); db.commit(); db.refresh(d)
            return {"created_drill_id": d.id, "fields": data}
        if name == "update_drill":
            did = args.get("drill_id")
            d = db.query(DrillModel).filter(DrillModel.id == did).first()
            if not d:
                return {"error": f"no existeix el drill {did}"}
            changed = {}
            for k, v in (args or {}).items():
                if k in ALLOWED and v is not None:
                    setattr(d, k, v); changed[k] = v
            db.commit()
            return {"updated_drill_id": did, "changed": changed}
        if name == "search_drills":
            from sqlalchemy import or_
            q = (args.get("query") or "").strip()
            lim = min(int(args.get("limit") or 10), 25)
            like = f"%{q}%"
            rows = (db.query(DrillModel).filter(or_(
                DrillModel.text_tachelhit.ilike(like), DrillModel.text_tachelhit_latin.ilike(like),
                DrillModel.text_catalan.ilike(like), DrillModel.text_arabic.ilike(like),
                DrillModel.tag.ilike(like))).limit(lim).all())
            return {"count": len(rows), "drills": [
                {"id": r.id, "catalan": r.text_catalan, "tachelhit": r.text_tachelhit,
                 "latin": r.text_tachelhit_latin} for r in rows]}
        if name == "what_can_a_practice_be_about":
            c = practice_mod.collections(db)
            return {k: c.get(k, [])[:40] for k in ("units", "topics", "people", "tags", "days")}
        if name == "find_sentences_for_practice":
            lim = min(int(args.get("limit") or 12), 40)
            picked = []
            if (args.get("query") or "").strip():
                from sqlalchemy import or_
                like = f"%{args['query'].strip()}%"
                rows = (grammar_course.not_excluded(db.query(DrillModel), DrillModel).filter(or_(
                    DrillModel.text_tachelhit.ilike(like), DrillModel.text_tachelhit_latin.ilike(like),
                    DrillModel.text_catalan.ilike(like), DrillModel.tag.ilike(like))).limit(300).all())
                picked = [r for r in rows if practice_mod.practicable(r)]
            else:
                picked = practice_mod.session_rows(
                    db, unit=args.get("unit"), topic=args.get("topic"), person=args.get("person"),
                    tag=args.get("tag"), day=args.get("day"), with_voice=True, limit=300)
            # shortest first: that is the order they are learned in
            picked.sort(key=lambda d: (len((d.text_tachelhit or "").split()), len(d.text_tachelhit or "")))
            return {"count": len(picked[:lim]), "sentences": [
                {"drill_id": r.id, "tachelhit": r.text_tachelhit, "catalan": r.text_catalan,
                 "has_picture": bool(r.image_url), "speaker": r.speaker or r.author}
                for r in picked[:lim]]}
        if name == "read_practice":
            t = db.query(TestModel).filter(TestModel.id == args.get("test_id")).first()
            if not t:
                return {"error": f"no existeix la pr\u00e0ctica {args.get('test_id')}"}
            return {"test_id": t.id, "title": t.title, "steps": practice_steps.steps_of(db, t.id)}
        if name == "add_to_practice":
            t = db.query(TestModel).filter(TestModel.id == args.get("test_id")).first()
            if not t:
                return {"error": f"no existeix la pr\u00e0ctica {args.get('test_id')}"}
            if not may_change(t, user):
                return {"error": "aquesta pr\u00e0ctica no \u00e9s teva; demana-ho a qui l'administra"}
            kept = [{"kind": x["kind"], "drill_id": x["drill_id"], "payload": x["payload"]}
                    for x in practice_steps.steps_of(db, t.id)]
            added = []
            for raw_step in (args.get("steps") or []):
                kind = (raw_step or {}).get("kind")
                one = {"kind": kind, "drill_id": raw_step.get("drill_id")}
                if kind == "note":
                    one["payload"] = {k: raw_step.get(k) for k in ("heading", "text") if raw_step.get(k)}
                added.append(one)
            if not added:
                return {"error": "no m'has dit cap pas per afegir"}
            try:
                written = practice_steps.replace_steps(db, t.id, kept + added)
            except practice_steps.StepError as e:
                return {"error": str(e)}
            return {"test_id": t.id, "added": len(added), "now": len(written)}
        if name == "illustrate_sentence":
            d = db.query(DrillModel).filter(DrillModel.id == args.get("drill_id")).first()
            if not d:
                return {"error": f"no existeix la frase {args.get('drill_id')}"}
            if (d.image_url or "").strip():
                return {"drill_id": d.id, "image_url": d.image_url, "note": "ja en tenia una"}
            if not illustration_available():
                return {"error": "ara mateix no es poden dibuixar imatges"}
            try:
                blob = generate_illustration(d.text_catalan or args.get("hint") or "", args.get("hint"))
                up = cloudinary.uploader.upload(
                    blob, folder="tachelhit/images",
                    public_id=f"img_{d.id}_{int(datetime.utcnow().timestamp())}")
                d.image_url = normalize_media_url(up["secure_url"])
                d.updated_at = datetime.utcnow()
                db.commit()
                return {"drill_id": d.id, "image_url": d.image_url}
            except Exception as e:
                db.rollback()
                return {"error": f"no s'ha pogut dibuixar: {str(e)[:120]}"}
        if name == "build_practice":
            t = db.query(TestModel).filter(TestModel.id == args.get("test_id")).first()
            if not t:
                return {"error": f"no existeix la pr\u00e0ctica {args.get('test_id')}"}
            if not may_change(t, user):
                return {"error": "aquesta pr\u00e0ctica no \u00e9s teva; dem-ho a qui l'administra"}
            steps = []
            for raw_step in (args.get("steps") or []):
                kind = (raw_step or {}).get("kind")
                step = {"kind": kind, "drill_id": raw_step.get("drill_id")}
                if kind == "note":
                    step["payload"] = {k: raw_step.get(k) for k in ("heading", "text") if raw_step.get(k)}
                steps.append(step)
            try:
                written = practice_steps.replace_steps(db, t.id, steps)
            except practice_steps.StepError as e:
                return {"error": str(e)}
            return {"test_id": t.id, "written": len(written),
                    "steps": [{"kind": x["kind"], "drill_id": x["drill_id"]} for x in written]}
        if name == "speak_tachelhit":
            text = (args.get("text") or "").strip()
            if not text:
                return {"error": "text buit"}
            try:
                url = generate_tachelhit_tts_hf(text, 0)
                return {"audio_url": normalize_media_url(url), "text": text}
            except Exception as e:
                return {"error": f"TTS ha fallat: {str(e)[:120]}"}
        return {"error": f"eina desconeguda: {name}"}
    return run

@app.post("/ai/agent")
def ai_agent(
    message: str = Body(..., embed=True),
    drill_ids: Optional[List[int]] = Body(None, embed=True),
    history: Optional[List[Dict]] = Body(None, embed=True),
    test_id: Optional[int] = Body(None, embed=True),
    db: Session = Depends(get_db),
    user: Optional[UserModel] = Depends(get_current_user),
    _gate: Dict[str, Any] = Depends(_ai_gate("agent")),
):
    """
    Agentic copilot: chat that can act on the app (create/update/search drills,
    speak Tachelhit) via Gemini function-calling, grounded in the grammar and
    the learner's corpus, aware of the currently-selected drill(s).
    """
    if not gemini_available():
        raise HTTPException(status_code=503, detail="AI assistant not configured (GEMINI_API_KEY missing)")
    if not (message or "").strip():
        raise HTTPException(status_code=400, detail="Empty message")

    system = _build_system_instruction(db) + (
        "\n\nEts un COPILOT que pot ACTUAR a l'aplicació amb les eines disponibles: "
        "crear i modificar drills, cercar-los i sintetitzar veu en taixelhit. "
        "Fes servir les eines quan l'usuari demani una acció (crea, edita, tradueix i desa, "
        "cerca/filtra, fes exemples per escoltar). Per a traduir i desar, actualitza el drill. "
        "Per a exemples parlats, crida speak_tachelhit. Confirma breument què has fet."
    )
    if test_id:
        system += (
            f"\n\nAra MATEIX l'usuari està fent la pràctica número {test_id} al taller. Quan et demani "
            "muntar-la, canviar-la o afegir-hi frases: mira què hi ha amb read_practice, busca les frases "
            "amb find_sentences_for_practice (o what_can_a_practice_be_about si no saps què hi ha a la "
            "biblioteca) i escriu-la amb build_practice. NOMÉS frases que t'hagin tornat aquelles eines: "
            "no te n'inventis cap id. Si vols afegir-ne a les que ja hi són, torna a escriure la "
            "seqüència sencera — o, millor, fes servir add_to_practice, que afegeix al final sense "
            "tocar el que ja hi ha.\n"
            "NO PREGUNTIS de què va la pràctica: mira-la amb read_practice i dedueix-ho de les seves "
            "frases i del seu nom. Si et demanen «més del mateix tema», busca frases que s'hi "
            "assemblin i afegeix-les. Si et demanen imatges, crida illustrate_sentence per a cada "
            "frase de la pràctica que no en tingui: les imatges van a les FRASES, i així les té "
            "tothom qui les faci servir. Fes les coses i després digues què has fet; pregunta "
            "només si de debò no es pot endevinar."
        )

    contents = []
    for turn in (history or [])[-8:]:
        contents.append({"role": turn.get("role", "user"), "text": turn.get("text", "")})

    # Selected-drill context
    selected = []
    for did in (drill_ids or [])[:10]:
        d = db.query(DrillModel).filter(DrillModel.id == did).first()
        if d:
            selected.append(f"#{d.id}: cat='{d.text_catalan}' tam='{d.text_tachelhit}' "
                            f"llatí='{d.text_tachelhit_latin}' àrab='{d.text_arabic}'")
    msg = message.strip()
    if selected:
        msg = "DRILLS SELECCIONATS:\n" + "\n".join(selected) + "\n\nMISSATGE: " + msg
    contents.append({"role": "user", "text": msg})

    try:
        result = gemini_agent(system, contents, AGENT_TOOLS, _agent_executor(db, user))
        return {"answer": result["text"], "actions": result["actions"]}
    except BudgetExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        print(f"[AI] agent failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI assistant error: {str(e)[:200]}")

@app.post("/ai/review-drill/{drill_id}")
def ai_review_drill(drill_id: int, db: Session = Depends(get_db), _gate: Dict[str, Any] = Depends(_ai_gate("review"))):
    """
    Contradiction-flagging: the AI checks a drill for likely transcription
    errors, Catalan↔Tachelhit mismatches, or spelling inconsistencies vs the
    glossary/grammar. It flags things to REVIEW — it does not "correct" the
    attested form (which is authoritative for its variety).
    """
    if not gemini_available():
        raise HTTPException(status_code=503, detail="AI assistant not configured (GEMINI_API_KEY missing)")
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")

    prompt = (
        _drill_context(drill) + "\n\n"
        "Revisa aquest drill com a lingüista i marca possibles problemes PER REVISAR "
        "(no corregeixis la forma attestada, només assenyala coses a comprovar):\n"
        "- El taixelhit i el català es corresponen realment?\n"
        "- Hi ha errors probables de transcripció (ASR), lletres barrejades o inconsistències d'ortografia?\n"
        "- La transliteració llatina concorda amb el tifinag?\n"
        "Respon amb un breu veredicte ('sembla correcte' / 'cal revisar') i una llista curta de punts concrets. "
        "Sigues concís."
    )
    try:
        review = gemini_generate(_build_system_instruction(db),
                                 [{"role": "user", "text": prompt}], max_output_tokens=600)
        return {"drill_id": drill_id, "review": review}
    except BudgetExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        print(f"[AI] review-drill failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI assistant error: {str(e)[:200]}")

# ===================== CORPUS (documentation & research) =====================

CORPUS_EXPORT_FIELDS = [
    "id", "date_created", "tag", "author", "speaker", "variety", "region",
    "license", "source_url", "verified", "text_catalan", "text_tachelhit",
    "text_tachelhit_latin", "text_arabic", "audio_url", "audio_tts_url",
    "video_url", "image_url", "video_start_time", "video_end_time"
]

@app.post("/corpus/reindex-keys")
def reindex_keys(db: Session = Depends(get_db)):
    """Backfill the phonemic key for every drill (one-time / after import)."""
    from transliteration import phonemic_key
    updated = 0
    for d in db.query(DrillModel).all():
        src = (d.text_tachelhit_latin or "").strip() or (d.text_tachelhit or "").strip()
        new_key = phonemic_key(src) if src else None
        if new_key != d.text_key:
            d.text_key = new_key
            updated += 1
    db.commit()
    return {"reindexed": updated}


@app.get("/corpus/search", response_model=list[Drill])
def corpus_search(
    q: Optional[str] = None,
    variety: Optional[str] = None,
    region: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Search the corpus across all text fields; filter by variety/region/tag.
    Paginate with limit/offset."""
    from sqlalchemy import or_
    # Les etiquetes excloses (proves, irlandès) no surten a la cerca: qui busca una frase busca
    # la llengua d'aquesta biblioteca, no el que hi ha entrat per fer proves.
    query = grammar_course.not_excluded(db.query(DrillModel), DrillModel)
    if q:
        like = f"%{q}%"
        from transliteration import phonemic_key as _pk
        conds = [
            DrillModel.text_tachelhit.ilike(like),
            DrillModel.text_tachelhit_latin.ilike(like),
            DrillModel.text_catalan.ilike(like),
            DrillModel.text_arabic.ilike(like),
        ]
        # cross-spelling / cross-script match via the phonemic key (so a query
        # typed as "aghrum", "aɣrum" or "ⴰⵖⵔⵓⵎ" all find the same drill)
        qkey = _pk(q)
        if qkey.strip():
            conds.append(DrillModel.text_key.ilike(f"%{qkey}%"))
        query = query.filter(or_(*conds))
    if variety:
        query = query.filter(DrillModel.variety == variety)
    if region:
        query = query.filter(DrillModel.region == region)
    if tag:
        query = query.filter(DrillModel.tag == tag)
    return query.order_by(DrillModel.date_created.desc()).offset(max(0, offset)).limit(min(limit, 500)).all()

@app.get("/corpus/export")
def corpus_export(format: str = "json", db: Session = Depends(get_db)):
    """
    Full corpus export (json or csv): every drill with all text, media and
    provenance fields. The corpus should never be trapped in one database.
    """
    drills = db.query(DrillModel).order_by(DrillModel.id).all()
    rows = []
    for d in drills:
        row = {}
        for f in CORPUS_EXPORT_FIELDS:
            v = getattr(d, f, None)
            row[f] = v.isoformat() if f == "date_created" and v else v
        rows.append(row)

    if format == "csv":
        import csv
        import io
        from fastapi.responses import Response
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CORPUS_EXPORT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=tachelhit_corpus.csv"}
        )
    return {"count": len(rows), "drills": rows}

@app.get("/corpus/flywheel")
def corpus_flywheel(verified_only: bool = False, format: str = "json", db: Session = Depends(get_db)):
    """
    (audio, text) pairs for fine-tuning ASR/translation models — the data
    flywheel: every human-verified drill improves the models that power
    capture for the whole language. verified_only=true restricts the export
    to human-reviewed items (recommended for training).
    """
    from sqlalchemy import or_
    query = db.query(DrillModel).filter(
        DrillModel.audio_url != None, DrillModel.audio_url != '',
        DrillModel.text_tachelhit != None, DrillModel.text_tachelhit != '',
        # Respect per-recording consent: private contributions never leave
        or_(DrillModel.license == None, DrillModel.license != 'private')
    )
    if verified_only:
        query = query.filter(DrillModel.verified == True)
    drills = query.all()
    pairs = [{
        "drill_id": d.id,
        "audio_url": normalize_media_url(d.audio_url),
        "text_tachelhit": d.text_tachelhit,
        "text_tachelhit_latin": d.text_tachelhit_latin,
        "text_catalan": d.text_catalan,
        "text_arabic": d.text_arabic,
        "variety": d.variety,
        "region": d.region,
        "license": d.license,
    } for d in drills]

    if format == "jsonl":
        # One JSON object per line — directly loadable with
        # datasets.load_dataset("json", data_files=...) for fine-tuning
        from fastapi.responses import Response
        lines = "\n".join(json.dumps(p, ensure_ascii=False) for p in pairs)
        return Response(
            content=lines,
            media_type="application/x-ndjson",
            headers={"Content-Disposition": "attachment; filename=tachelhit_flywheel.jsonl"}
        )
    return {"count": len(pairs), "pairs": pairs}

#: Els dibuixos de l'app: els que expliquen què és cada part, no els d'una frase.
#:
#: Viuen a la base de dades i no al codi perquè es puguin canviar sense desplegar res — es
#: dibuixen un dia, es miren, i el que no agrada es torna a dibuixar. Cada joc és un diccionari
#: {nom: adreça}: «home» per a les portes de la portada, «method» per als capítols del Mètode.
ARTWORK = ("home", "method")


def artwork(db, which: str) -> Dict[str, str]:
    """Els dibuixos d'un joc, o un diccionari buit si encara no n'hi ha cap."""
    row = db.query(AppSettingModel).filter(AppSettingModel.key == f"artwork_{which}").first()
    if not row or not (row.value or "").strip():
        return {}
    try:
        got = json.loads(row.value)
    except Exception:
        return {}
    return {str(k): v for k, v in got.items() if isinstance(v, str) and v.strip()} if isinstance(got, dict) else {}


@app.get("/artwork")
def get_artwork(db: Session = Depends(get_db)):
    """Els dibuixos de l'app, per joc. Qualsevol els pot llegir: són el que es veu a la pantalla."""
    return {w: artwork(db, w) for w in ARTWORK}


@app.put("/artwork/{which}")
def put_artwork(which: str, covers: Dict[str, Optional[str]] = Body(..., embed=True),
                db: Session = Depends(get_db), _admin: UserModel = Depends(require_admin)):
    """Desa els dibuixos d'un joc. Una adreça buida treu el dibuix i torna al que hi havia."""
    if which not in ARTWORK:
        raise HTTPException(status_code=404, detail=f"«{which}» no és cap joc de dibuixos")
    keep = {str(k): v.strip() for k, v in covers.items() if isinstance(v, str) and v.strip()}
    row = db.query(AppSettingModel).filter(AppSettingModel.key == f"artwork_{which}").first()
    if row is None:
        row = AppSettingModel(key=f"artwork_{which}")
        db.add(row)
    row.value = json.dumps(keep, ensure_ascii=False)
    db.commit()
    return {"which": which, "covers": keep}


@app.get("/home")
def home(db: Session = Depends(get_db),
         user: Optional[UserModel] = Depends(get_current_user)):
    """El que hi ha a casa: les portes de l'app i quant hi ha darrere de cadascuna.

    La portada era la graella de drills, i per això l'app semblava una taula amb coses penjades
    al voltant. Això són els NOMBRES que fan que la portada digui alguna cosa: quantes frases hi
    ha i quantes es poden escoltar, quants capítols del Mètode estan escrits, quantes unitats
    tenen lliçó, quantes pràctiques hi ha i quantes són teves, i quantes frases esperen una veu.

    Tot són comptes: no en surt cap fila. La graella de drills pesa sis megues i no pot ser el
    que es carrega en obrir l'app.
    """
    from sqlalchemy import func

    from models import GrammarLesson, MethodChapter
    mine = grammar_course.not_excluded(db.query(DrillModel), DrillModel)
    voiced = mine.filter(DrillModel.audio_url.isnot(None), DrillModel.audio_url != "")
    lessons = db.query(func.count(GrammarLesson.id)).filter(
        ~GrammarLesson.id.like("sheet:%"), ~GrammarLesson.id.like("deep:%")).scalar() or 0

    # Una imatge per porta, de les NOSTRES: les il·lustracions que fem per a una frase, que són
    # les que ja es veuen a tot arreu de l'app. Mai una imatge trobada per la xarxa (vegeu
    # `grammar.our_picture`): a la portada enganyaria igual que enganyava en una pregunta.
    # Les il·lustracions que dibuixem per a una frase primer, i els fotogrames de vídeo després:
    # un dibuix fet per a aquella frase diu alguna cosa, i un fotograma qualsevol no. Van en dues
    # consultes perquè, en una de sola, els últims vuitanta drills són tot fotogrames.
    def pictures(only_drawn: bool):
        q = db.query(DrillModel.image_url, DrillModel.grammar, DrillModel.tag, DrillModel.source_url) \
              .filter(DrillModel.image_url.isnot(None), DrillModel.image_url != "")
        q = q.filter(DrillModel.image_url.ilike("%/illustrations/%") if only_drawn
                     else ~DrillModel.image_url.ilike("%/illustrations/%"))
        return [r for r in q.order_by(DrillModel.id.desc()).limit(40).all()
                if grammar_course.our_picture(r[0])]

    pool = pictures(True) + pictures(False)
    taken: set = set()
    from_video: set = set()

    def cover(*wants) -> Optional[str]:
        """La primera imatge que compleix el que la porta demana, i si no, la següent lliure.

        Dues portes no ensenyen mai dos fotogrames del MATEIX vídeo: serien la mateixa cara dues
        vegades i la portada semblaria trencada.
        """
        for want in (*wants, lambda r: True):
            for r in pool:
                if r[0] in taken or (r[3] and r[3] in from_video) or not want(r):
                    continue
                taken.add(r[0])
                if r[3]:
                    from_video.add(r[3])
                return r[0]
        return None

    # Si hi ha dibuixos fets per a les portes (`/artwork`), manen: són els que expliquen què és
    # cada part. Mentre no n'hi hagi, s'agafa una imatge de la biblioteca, que és millor que res.
    drawn = artwork(db, "home")

    def pick(door, *wants):
        return drawn.get(door) or cover(*wants)

    covers = {
        "method": pick("method", lambda r: "metode" in (r[2] or "").lower()),
        "grammar": pick("grammar", lambda r: bool(r[1])),
        "practice": pick("practice", lambda r: bool(r[1])),
        "library": pick("library"),
        "stories": pick("stories", lambda r: bool(r[3])),
        "capture": pick("capture", lambda r: bool(r[3])),
    }
    tests = db.query(func.count(TestModel.id)).scalar() or 0
    return {
        "library": {
            "sentences": mine.count(),
            "with_voice": voiced.count(),
            "speakers": db.query(func.count(func.distinct(DrillModel.author))).filter(
                DrillModel.author.isnot(None), DrillModel.author != "",
                DrillModel.audio_url.isnot(None), DrillModel.audio_url != "").scalar() or 0,
            "varieties": db.query(func.count(func.distinct(DrillModel.variety))).filter(
                DrillModel.variety.isnot(None), DrillModel.variety != "").scalar() or 0,
            "videos": db.query(func.count(func.distinct(DrillModel.source_url))).filter(
                DrillModel.source_url.isnot(None), DrillModel.source_url != "").scalar() or 0,
            # el que espera una veu: és la feina que hi ha, dita en un número
            "wanted": mine.filter(DrillModel.voice_wanted.is_(True),
                                  (DrillModel.audio_url.is_(None)) | (DrillModel.audio_url == "")).count(),
        },
        "covers": covers,
        "method": {"chapters": len(method_mod.CHAPTERS),
                   "written": db.query(func.count(MethodChapter.slug)).scalar() or 0},
        "grammar": {"units": len(grammar_course.UNITS), "with_lesson": lessons},
        "practice": {"all": tests,
                     "mine": (db.query(func.count(TestModel.id)).filter(
                         TestModel.created_by_user_id == user.id).scalar() or 0) if user else 0},
        "you": {
            "signed_in": bool(user),
            "name": (user.display_name or user.username) if user else None,
            "is_admin": bool(user and user.is_admin),
            "recordings": (db.query(func.count(RecordingModel.id)).filter(
                RecordingModel.user_id == user.id).scalar() or 0) if user else 0,
        },
    }


@app.get("/corpus/stats")
def corpus_stats(db: Session = Depends(get_db)):
    """Corpus health overview: sizes, media coverage, varieties, regions."""
    from sqlalchemy import func
    total = db.query(DrillModel).count()
    with_audio = db.query(DrillModel).filter(DrillModel.audio_url != None, DrillModel.audio_url != '').count()
    with_video = db.query(DrillModel).filter(DrillModel.video_url != None, DrillModel.video_url != '').count()
    with_latin = db.query(DrillModel).filter(DrillModel.text_tachelhit_latin != None, DrillModel.text_tachelhit_latin != '').count()
    verified = db.query(DrillModel).filter(DrillModel.verified == True).count()
    by_variety = {str(k or "unspecified"): v for k, v in db.query(DrillModel.variety, func.count()).group_by(DrillModel.variety).all()}
    by_region = {str(k or "unspecified"): v for k, v in db.query(DrillModel.region, func.count()).group_by(DrillModel.region).all()}
    return {
        "total_drills": total,
        "with_audio": with_audio,
        "with_video": with_video,
        "with_latin_script": with_latin,
        "verified": verified,
        "by_variety": by_variety,
        "by_region": by_region,
    }

_TITLE_NOISE = re.compile(r"\s*[\(\[][^()\[\]]*(subtit|lyrics|paroles|official (music )?video|official clip|translated)[^()\[\]]*[\)\]]", re.I)


def display_title(title: Optional[str]) -> Optional[str]:
    """The source title for the catalog: provenance keeps the uploader's exact title,
    the catalog drops boilerplate such as "(With English, French … subtitles)"."""
    if not title:
        return title
    t = _TITLE_NOISE.sub("", title)
    t = re.sub(r"\s{2,}", " ", t).strip(" -|·")
    return t or title


@app.get("/corpus/sources")
def corpus_sources(db: Session = Depends(get_db)):
    """The catalog: every source video the drills came from, grouped
    channel > playlist > video, with counts, media coverage, variety, the span of
    the video covered and the tag(s) used — plus how many drills have no source
    (speaker recordings)."""
    rows = db.query(DrillModel).filter(DrillModel.source_url != None, DrillModel.source_url != '').all()
    videos: Dict[str, Dict[str, Any]] = {}
    for d in rows:
        # agrupat pel VÍDEO: la mateixa captura escriu una URL diferent per tall (hi posa el
        # segon on comença), i agrupar per la cadena comptava un vídeo per cada tall
        v = videos.setdefault(video_key(d.source_url), {
            "source_url": d.source_url, "title": None, "channel": None, "playlist": None, "license": None,
            "drills": 0, "with_video": 0, "with_audio": 0, "verified": 0, "varieties": set(), "tags": set(),
            "from_s": None, "to_s": None, "ids": []})
        v["drills"] += 1
        v["ids"].append(d.id)
        v["title"] = v["title"] or display_title(d.source_title)
        v["channel"] = v["channel"] or d.source_channel
        v["playlist"] = v["playlist"] or d.source_playlist
        v["license"] = v["license"] or d.license
        v["with_video"] += 1 if d.video_url else 0
        v["with_audio"] += 1 if d.audio_url else 0
        v["verified"] += 1 if d.verified else 0
        if d.variety:
            v["varieties"].add(d.variety)
        if d.tag:
            v["tags"].add(d.tag)
        if d.video_start_time is not None:
            v["from_s"] = d.video_start_time if v["from_s"] is None else min(v["from_s"], d.video_start_time)
        if d.video_end_time is not None:
            v["to_s"] = d.video_end_time if v["to_s"] is None else max(v["to_s"], d.video_end_time)
    out = []
    for v in videos.values():
        v["varieties"] = sorted(v["varieties"])
        v["tags"] = sorted(v["tags"])
        v["first_id"] = min(v["ids"])
        del v["ids"]
        out.append(v)
    out.sort(key=lambda v: ((v["channel"] or "~"), (v["playlist"] or "~"), -v["drills"]))
    total = db.query(DrillModel).count()
    return {"total_drills": total, "from_sources": len(rows), "without_source": total - len(rows),
            "channels": len({v["channel"] for v in out if v["channel"]}), "videos": out}

# Documentation-gap definitions: (key, human label, SQLAlchemy filter builder).
# A "gap" is a drill that has Tachelhit content but is missing some dimension a
# complete corpus entry should have — the work-list for contributors.
def _gap_filters():
    from sqlalchemy import or_, and_
    has_tachelhit = and_(DrillModel.text_tachelhit != None, DrillModel.text_tachelhit != '')
    empty = lambda col: or_(col == None, col == '')
    return {
        "no_audio":   ("Sense àudio (cal una gravació)", and_(has_tachelhit, empty(DrillModel.audio_url))),
        # only meaningful when the text itself is in Tifinagh (Latin text IS the romanization)
        "no_latin":   ("Sense romanització llatina", and_(has_tachelhit, empty(DrillModel.text_tachelhit_latin),
                                                          DrillModel.text_tachelhit.regexp_match("[ⴰ-⵿]"))),
        "no_catalan": ("Sense traducció catalana", and_(has_tachelhit, empty(DrillModel.text_catalan))),
        "no_arabic":  ("Sense àrab", and_(has_tachelhit, empty(DrillModel.text_arabic))),
        "no_variety": ("Sense varietat/regió", and_(has_tachelhit, empty(DrillModel.variety))),
        # verified defaults to NULL; `verified != True` excludes NULLs in SQL,
        # so match NULL and False explicitly (both mean "not yet verified")
        "unverified": ("Pendent de verificar", and_(has_tachelhit,
                       or_(DrillModel.verified.is_(None), DrillModel.verified.is_(False)))),
    }

@app.get("/corpus/gaps")
def corpus_gaps(kind: Optional[str] = None, limit: int = 100, offset: int = 0,
                db: Session = Depends(get_db)):
    """
    Documentation completeness. Without `kind`: a count per gap type (the
    work-list summary). With `kind`: the actual drills needing that work,
    so contributors can jump straight to filling them.
    """
    filters = _gap_filters()
    if kind is None:
        return {
            "total": db.query(DrillModel).count(),
            "gaps": [
                {"kind": k, "label": label,
                 "count": db.query(DrillModel).filter(flt).count()}
                for k, (label, flt) in filters.items()
            ]
        }
    if kind not in filters:
        raise HTTPException(status_code=400, detail=f"Unknown gap kind. Options: {list(filters)}")
    _, flt = filters[kind]
    rows = (
        db.query(DrillModel).filter(flt)
        .order_by(DrillModel.date_created.desc())
        .offset(max(0, offset)).limit(min(limit, 500)).all()
    )
    return {"kind": kind, "drills": [Drill.model_validate(r, from_attributes=True) for r in rows]}

# ===================== SPEAKER VERIFICATION QUEUE =====================
# The listening review (tools/review_heard.py) writes what the machine listeners heard in
# front of text_tachelhit_suggested: "[heard]" when two listeners agree, "[? a | b]" when
# they disagree. Nothing there is gold. The queue hands every doubtful recording to a
# speaker, one at a time, and `resolve` records the speaker's decision.

_HEARD_RE = re.compile(r"^\s*\[(\?)?\s*([^\]]*)\]")

VERIFY_REASONS = {
    "differs":   "El que se sent no coincideix amb el text",
    "contested": "Les dues escoltes no coincideixen",
    "empty":     "Gravació sense text",
    "subtitle":  "Només la lectura del subtítol, sense confirmar",
    "confirm":   "La màquina hi està d'acord: només cal confirmar-ho",
}


def parse_heard(suggested: Optional[str]):
    """-> (options, contested, rest): the bracketed readings, whether the listeners
    disagreed, and whatever other suggestion follows the bracket."""
    s = (suggested or "").strip()
    m = _HEARD_RE.match(s)
    if not m:
        return [], False, s
    opts = list(dict.fromkeys(o.strip() for o in m.group(2).split("|") if o.strip()))
    return opts, bool(m.group(1)), s[m.end():].strip(" ·")


def reading_similarity(a: str, b: str) -> float:
    """Script-independent closeness of two Tachelhit readings (phonemic keys)."""
    import difflib
    from transliteration import phonemic_key
    ka, kb = phonemic_key(a or ""), phonemic_key(b or "")
    if not ka or not kb:
        return 0.0
    return difflib.SequenceMatcher(None, ka, kb).ratio()


def verify_queue_reason(d) -> Optional[tuple]:
    """(reason, options) when a speaker should listen to this drill, else None."""
    if d.verified:
        return None
    if not ((d.audio_url or "").strip() or (d.video_url or "").strip()):
        return None  # nothing to listen to
    stored = (d.text_tachelhit or "").strip()
    latin = (d.text_tachelhit_latin or "").strip()
    opts, contested, rest = parse_heard(d.text_tachelhit_suggested)
    if not stored:
        if rest or latin:
            return "subtitle", list(dict.fromkeys([x for x in [rest, latin] if x] + opts))
        return "empty", opts
    if not opts:
        return None
    if contested:
        return "contested", opts
    if max(reading_similarity(o, stored) for o in opts) < 0.6:
        return "differs", opts
    return "confirm", opts  # the listeners agree with the stored text: one tap to verify


@app.get("/corpus/verify-queue")
def corpus_verify_queue(reason: Optional[str] = None, limit: int = 100, offset: int = 0,
                        db: Session = Depends(get_db)):
    """Recorded drills a speaker still has to confirm by ear, most doubtful first.
    `limit=0` returns only the counts."""
    from sqlalchemy import or_
    if reason is not None and reason not in VERIFY_REASONS:
        raise HTTPException(status_code=400, detail=f"Unknown reason. Options: {list(VERIFY_REASONS)}")
    order = list(VERIFY_REASONS)
    items = []
    for d in db.query(DrillModel).filter(or_(DrillModel.verified.is_(None), DrillModel.verified.is_(False))).all():
        hit = verify_queue_reason(d)
        if hit:
            items.append((d, hit[0], hit[1]))
    counts = {k: sum(1 for _, r, _ in items if r == k) for k in order}
    if reason:
        items = [it for it in items if it[1] == reason]
    items.sort(key=lambda it: (order.index(it[1]), it[0].id))
    page = items[max(0, offset): max(0, offset) + min(limit, 500)] if limit > 0 else []
    return {
        "total": len(items), "counts": counts, "labels": VERIFY_REASONS,
        "drills": [dict(Drill.model_validate(d, from_attributes=True).model_dump(), reason=r, heard=opts)
                   for d, r, opts in page],
    }


class ResolveBody(BaseModel):
    text_tachelhit: Optional[str] = None  # the reading the speaker confirms; None keeps the stored text


@app.post("/drills/{drill_id}/resolve", response_model=Drill)
def resolve_drill(drill_id: int, body: ResolveBody, db: Session = Depends(get_db),
                  user: Optional[UserModel] = Depends(get_current_user)):
    """A speaker's verdict from the verification queue: set the text they confirm (or keep
    what is stored), drop the machine bracket from the suggestion, mark the drill verified."""
    if not user:
        raise HTTPException(status_code=401, detail="Verification requires a registered user (X-User-Token)")
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
    text = (body.text_tachelhit or "").strip()
    if text:
        drill.text_tachelhit = text
        if not (drill.text_tachelhit_latin or "").strip() and not re.search(r"[\u2d30-\u2d7f]", text):
            drill.text_tachelhit_latin = text
    elif not (drill.text_tachelhit or "").strip():
        raise HTTPException(status_code=400, detail="This drill has no text yet: send the text the speaker confirms")
    _, _, rest = parse_heard(drill.text_tachelhit_suggested)
    drill.text_tachelhit_suggested = rest if rest and rest != (drill.text_tachelhit or "").strip() else None
    drill.verified = True
    drill.verified_by_user_id = user.id
    _set_drill_key(drill)
    db.commit()
    db.refresh(drill)
    return drill


# ===================== PRONUNCIATION CHECK =====================

def _normalize_for_comparison(text: str) -> str:
    """Lowercase, strip punctuation/extra whitespace for fuzzy comparison."""
    cleaned = re.sub(r"[^\w\sⴰ-⵿]", "", (text or "").lower(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned).strip()

def apply_glossary(text: str, pairs) -> str:
    """
    Word-boundary-aware sound->spelling normalization. `pairs` is an iterable
    of (word_sound, correct_spelling). Boundaries matter: flat substring
    replacement would also rewrite matches *inside* longer words (\\w covers
    Tifinagh and Arabic letters in Python's Unicode mode).
    """
    for sound, spelling in pairs:
        if sound:
            text = re.sub(rf"(?<!\w){re.escape(sound)}(?!\w)", spelling, text)
    return text



@app.get("/reviews/due", response_model=list[Drill])
def get_due_reviews(limit: int = 20, db: Session = Depends(get_db),
                    user: Optional[UserModel] = Depends(get_current_user)):
    """
    Drills due for spaced-repetition review for THIS user (anonymous requests
    get the shared legacy schedule): overdue cards first, then never-reviewed
    drills (newest first) to fill up.
    """
    uid = user.id if user else None
    now = datetime.utcnow()
    due_rows = (
        db.query(DrillModel)
        .join(DrillReviewModel, DrillReviewModel.drill_id == DrillModel.id)
        .filter(DrillReviewModel.user_id == uid, DrillReviewModel.due_date <= now)
        .order_by(DrillReviewModel.due_date.asc())
        .limit(limit)
        .all()
    )
    drills = list(due_rows)
    if len(drills) < limit:
        from sqlalchemy import or_, and_
        seen = db.query(DrillReviewModel.drill_id).filter(DrillReviewModel.user_id == uid)
        new_drills = (
            db.query(DrillModel)
            .filter(
                ~DrillModel.id.in_(seen),
                # Only practiceable cards: there must be a voice or a text to recall
                or_(
                    and_(DrillModel.text_tachelhit != None, DrillModel.text_tachelhit != ''),
                    and_(DrillModel.audio_url != None, DrillModel.audio_url != '')
                )
            )
            .order_by(DrillModel.date_created.desc())
            .limit(limit - len(drills))
            .all()
        )
        drills.extend(new_drills)
    return drills

def _apply_sm2_grade(db, drill_id: int, uid: Optional[int], grade: int, now: datetime):
    """Reschedule one card for one user (SM-2) and log the grade at `now`.
    Shared by the single and batch grade endpoints (P4.9). Caller commits."""
    review = db.query(DrillReviewModel).filter(
        DrillReviewModel.drill_id == drill_id, DrillReviewModel.user_id == uid
    ).first()
    if not review:
        review = DrillReviewModel(
            drill_id=drill_id, user_id=uid, ease=2.5, interval_days=0.0,
            repetitions=0, total_reviews=0, lapses=0, due_date=now
        )
        db.add(review)

    if grade == 0:  # again — lapse, back to the start, retry this session
        review.repetitions = 0
        review.lapses += 1
        review.ease = max(1.3, review.ease - 0.2)
        review.interval_days = 0.007  # ~10 minutes
    elif grade == 1:  # hard
        review.ease = max(1.3, review.ease - 0.15)
        review.interval_days = 0.5 if review.repetitions == 0 else review.interval_days * 1.2
        review.repetitions += 1
    elif grade == 2:  # good
        if review.repetitions == 0:
            review.interval_days = 1.0
        elif review.repetitions == 1:
            review.interval_days = 6.0
        else:
            review.interval_days = review.interval_days * review.ease
        review.repetitions += 1
    else:  # easy
        review.ease = min(3.0, review.ease + 0.15)
        if review.repetitions == 0:
            review.interval_days = 2.0
        elif review.repetitions == 1:
            review.interval_days = 8.0
        else:
            review.interval_days = review.interval_days * review.ease * 1.3
        review.repetitions += 1

    review.due_date = now + timedelta(days=review.interval_days)
    review.last_grade = grade
    review.last_reviewed = now
    review.total_reviews += 1
    review.updated_at = now
    db.add(ReviewLogModel(drill_id=drill_id, user_id=uid, grade=grade, reviewed_at=now))
    return review

@app.post("/reviews/{drill_id}/grade")
def grade_review(drill_id: int, grade: int = Body(..., embed=True), db: Session = Depends(get_db),
                 user: Optional[UserModel] = Depends(get_current_user)):
    """Record a review grade for this user and reschedule the drill (SM-2)."""
    if grade not in (0, 1, 2, 3):
        raise HTTPException(status_code=400, detail="grade must be 0 (again), 1 (hard), 2 (good) or 3 (easy)")
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")

    uid = user.id if user else None
    review = _apply_sm2_grade(db, drill_id, uid, grade, datetime.utcnow())
    db.commit()
    db.refresh(review)
    return {
        "drill_id": drill_id,
        "next_due": iso_z(review.due_date),
        "interval_days": round(review.interval_days, 3),
        "ease": round(review.ease, 2),
        "repetitions": review.repetitions
    }

class GradeBatchItem(BaseModel):
    drill_id: int
    grade: int = Field(..., ge=0, le=3)
    graded_at: datetime  # ISO-8601; "Z" / offsets accepted, naive = UTC

@app.post("/reviews/grade-batch")
def grade_batch(items: List[GradeBatchItem], db: Session = Depends(get_db),
                user: Optional[UserModel] = Depends(get_current_user)):
    """Apply grades queued offline (P4.9), oldest first, through the same SM-2
    logic as /reviews/{id}/grade. Idempotent on (user, drill, graded_at): a
    grade whose ReviewLog row already exists is skipped, so a client may
    re-send its whole queue after a lost response without double-scheduling.
    Grades for drills that no longer exist are skipped too."""
    uid = user.id if user else None
    applied = 0
    skipped = 0
    for it in sorted(items, key=lambda i: _to_naive_utc(i.graded_at)):
        ts = _to_naive_utc(it.graded_at)
        dup = db.query(ReviewLogModel.id).filter(
            ReviewLogModel.user_id == uid,
            ReviewLogModel.drill_id == it.drill_id,
            ReviewLogModel.reviewed_at == ts,
        ).first()
        if dup is not None:
            skipped += 1
            continue
        if db.query(DrillModel.id).filter(DrillModel.id == it.drill_id).first() is None:
            skipped += 1
            continue
        _apply_sm2_grade(db, it.drill_id, uid, it.grade, ts)
        db.flush()  # so a duplicate later in the SAME batch is seen as applied
        applied += 1
    db.commit()
    return {"applied": applied, "skipped": skipped}

@app.post("/tests/from-weakest")
def create_test_from_weakest(
    count: int = Body(10, embed=True),
    db: Session = Depends(get_db),
    user: Optional[UserModel] = Depends(get_current_user)
):
    """
    Build a test from the requesting user's weakest cards (lowest ease, most
    lapses first), topping up with recent drills if there isn't enough review
    history yet. Closes the loop between SRS data and testing.
    """
    uid = user.id if user else None
    count = max(3, min(count, 30))

    weakest = (
        db.query(DrillReviewModel)
        .filter(DrillReviewModel.user_id == uid)
        .order_by(DrillReviewModel.ease.asc(), DrillReviewModel.lapses.desc())
        .limit(count)
        .all()
    )
    drill_ids = [r.drill_id for r in weakest]

    if len(drill_ids) < count:
        q = db.query(DrillModel.id).filter(
            DrillModel.text_tachelhit != None,
            DrillModel.text_tachelhit != ''
        )
        if drill_ids:
            q = q.filter(~DrillModel.id.in_(drill_ids))
        extra = q.order_by(DrillModel.date_created.desc()).limit(count - len(drill_ids)).all()
        drill_ids += [row[0] for row in extra]

    if not drill_ids:
        raise HTTPException(status_code=400, detail="No drills available to build a test from")

    test = TestModel(
        title=f"💪 Punts febles {datetime.utcnow().strftime('%d/%m')}",
        description="Generat automàticament amb les teves targetes més difícils",
        question_type="text_input",
        hint_level="partial",
        hint_percentage=30,
        passing_score=70.0,
        drill_ids=",".join(str(i) for i in drill_ids),
        created_by_user_id=uid,          # it is built from THEIR review history: it is theirs
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return {"test_id": test.id, "title": test.title, "drill_count": len(drill_ids)}

@app.get("/reviews/streak")
def review_streak(db: Session = Depends(get_db),
                  user: Optional[UserModel] = Depends(get_current_user)):
    """Daily streak and activity counts for the requesting user."""
    uid = user.id if user else None
    zone = _user_zone(user)  # "today" in the learner's zone, not UTC (P4.10)
    rows = db.query(ReviewLogModel.reviewed_at).filter(ReviewLogModel.user_id == uid).all()
    local_days = [_local_day(r[0], zone) for r in rows]
    days = set(local_days)
    today = datetime.now(timezone.utc).astimezone(zone).date()

    # Streak of consecutive review days; still alive if yesterday was reviewed
    streak = 0
    if today in days:
        cursor = today
    elif (today - timedelta(days=1)) in days:
        cursor = today - timedelta(days=1)
    else:
        cursor = None
    while cursor is not None and cursor in days:
        streak += 1
        cursor = cursor - timedelta(days=1)

    week_ago = today - timedelta(days=6)
    return {
        "streak_days": streak,
        "reviews_today": sum(1 for d in local_days if d == today),
        "reviews_week": sum(1 for d in local_days if d >= week_ago),
        "active_days": len(days),
        "tz": getattr(zone, "key", "UTC"),
        "today": today.isoformat(),
    }

@app.get("/reviews/stats")
def review_stats(db: Session = Depends(get_db),
                 user: Optional[UserModel] = Depends(get_current_user)):
    """Counts for the home-screen review badge, scoped to the requesting user.
    `reviewed_today` counts grades on the learner's local day (P4.10)."""
    uid = user.id if user else None
    now = datetime.utcnow()
    zone = _user_zone(user)
    today = datetime.now(timezone.utc).astimezone(zone).date()
    total = db.query(DrillModel).count()
    tracked = db.query(DrillReviewModel).filter(DrillReviewModel.user_id == uid).count()
    due = db.query(DrillReviewModel).filter(
        DrillReviewModel.user_id == uid, DrillReviewModel.due_date <= now
    ).count()
    # local midnight -> UTC lower bound keeps this a cheap indexed range scan
    day_start_utc = datetime.combine(today, datetime.min.time(), tzinfo=zone) \
        .astimezone(timezone.utc).replace(tzinfo=None)
    reviewed_today = db.query(ReviewLogModel).filter(
        ReviewLogModel.user_id == uid, ReviewLogModel.reviewed_at >= day_start_utc
    ).count()
    return {
        "total_drills": total,
        "new": max(0, total - tracked),
        "due": due,
        "learning": tracked,
        "reviewed_today": reviewed_today,
        "today": today.isoformat(),
    }

# ===================== DEBUG ENDPOINTS =====================
# Added a comment to trigger Render deployment - 2026-02-24
@app.get("/debug/video-generation/{test_id}")
def debug_video_generation(test_id: int, db: Session = Depends(get_db)):
    """Debug endpoint to check video generation status for a test."""
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    # Get test drills
    drill_ids = [int(id.strip()) for id in test.drill_ids.split(',') if id.strip()]
    drills = db.query(DrillModel).filter(DrillModel.id.in_(drill_ids)).all()

    # Check audio URLs
    audio_status = []
    for drill in drills:
        audio_ok = False
        audio_tts_ok = False

        if drill.audio_url:
            try:
                import requests
                response = requests.head(drill.audio_url, timeout=5)
                audio_ok = response.status_code == 200
            except:
                audio_ok = False

        if drill.audio_tts_url:
            try:
                import requests
                response = requests.head(drill.audio_tts_url, timeout=5)
                audio_tts_ok = response.status_code == 200
            except:
                audio_tts_ok = False

        audio_status.append({
            "drill_id": drill.id,
            "text_catalan": drill.text_catalan,
            "audio_url": drill.audio_url,
            "audio_ok": audio_ok,
            "audio_tts_url": drill.audio_tts_url,
            "audio_tts_ok": audio_tts_ok,
            "image_url": drill.image_url
        })

    return {
        "test_id": test_id,
        "test_title": test.title,
        "video_url": test.video_url,
        "drill_count": len(drill_ids),
        "audio_status": audio_status,
        "huggingface_space_url": os.getenv("HUGGINGFACE_SPACE_URL"),
        "cloudinary_configured": bool(os.getenv("CLOUDINARY_CLOUD_NAME"))
    }

@app.get("/debug/moviepy")
def debug_moviepy():
    """Check if moviepy and ffmpeg are working."""
    try:
        from shorts_generator import MOVIEPY_AVAILABLE, MOVIEPY_ERROR
        status = {
            "moviepy_available": MOVIEPY_AVAILABLE,
            "moviepy_error": MOVIEPY_ERROR,
            "requirements_installed": True,
        }

        # Try to import imageio_ffmpeg
        try:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
            status["imageio_ffmpeg"] = {
                "version": imageio_ffmpeg.__version__,
                "ffmpeg_path": ffmpeg_path,
                "path_exists": os.path.exists(ffmpeg_path) if ffmpeg_path else False
            }
        except Exception as e:
            status["imageio_ffmpeg_error"] = str(e)

        # Try to import moviepy components
        if MOVIEPY_AVAILABLE:
            try:
                from moviepy.video.VideoClip import ImageClip
                from moviepy.video.io.VideoFileClip import VideoFileClip
                status["moviepy_import"] = "success"
            except Exception as e:
                status["moviepy_import_error"] = str(e)
        else:
            status["moviepy_import"] = "failed"

        # Check ffmpeg in PATH
        import shutil
        ffmpeg_path_sys = shutil.which('ffmpeg')
        status["system_ffmpeg"] = ffmpeg_path_sys

        # Check environment variable
        status["env_ffmpeg_binary"] = os.environ.get("FFMPEG_BINARY")

        return status
    except Exception as e:
        return {"error": str(e), "traceback": str(traceback.format_exc())}

@app.get("/debug/db")
def debug_db(db: Session = Depends(get_db)):
    """Debug endpoint to show database stats."""
    drill_count = db.query(DrillModel).count()
    test_count = db.query(TestModel).count()
    short_count = db.query(YouTubeShortModel).count()
    return {
        "drill_count": drill_count,
        "test_count": test_count,
        "short_count": short_count,
        "database_url": engine.url.render_as_string(hide_password=True),
        "development_mode": DEVELOPMENT_MODE
    }

@app.post("/debug/populate-sample")
def debug_populate_sample(token: Optional[str] = Body(None, embed=True), db: Session = Depends(get_db)):
    """Adds sample drills (ignores duplicates) - protected by ADMIN_TOKEN in production"""
    # Check for admin token in production
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
    if ADMIN_TOKEN and ADMIN_TOKEN.strip():
        # Production environment requires a valid token
        if not token or token != ADMIN_TOKEN:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized. Provide a valid 'token' in request body."
            )
    # If no ADMIN_TOKEN is set (development), allow without token
    try:
        samples = [
            DrillModel(
                text_catalan="Hola",
                text_tachelhit="ⴰⵣⵓⵍ",
                text_arabic="مرحبا",
                tag="greeting"
            ),
            DrillModel(
                text_catalan="Com et dius?",
                text_tachelhit="ⵎⴰⵏⵉⵙ ⵉⵙⵎ ⵏⵏⴽ?",
                text_arabic="ما اسمك؟",
                tag="introduction"
            ),
            DrillModel(
                text_catalan="Gràcies",
                text_tachelhit="ⵜⴰⵏⵎⵎⵉⵔⵜ",
                text_arabic="شكرا",
                tag="courtesy"
            )
        ]
        added_samples = []
        for sample in samples:
            # Check if a drill with same text exists (optional)
            existing = db.query(DrillModel).filter(
                DrillModel.text_catalan == sample.text_catalan
            ).first()
            if not existing:
                db.add(sample)
                added_samples.append(sample)
        db.commit()
        # Refresh IDs — only for instances actually inserted; refreshing a
        # transient (skipped duplicate) instance raises InvalidRequestError
        for sample in added_samples:
            db.refresh(sample)
        added = len(added_samples)
        return {
            "status": "success",
            "added": added,
            "total": db.query(DrillModel).count()
        }
    except Exception as e:
        db.rollback()
        print(f"[DEBUG] Error populating sample: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/seed")
def debug_seed(token: Optional[str] = None, db: Session = Depends(get_db)):
    """GET endpoint to add sample drills (ignores duplicates) - protected by ADMIN_TOKEN in production"""
    # Check for admin token in production
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
    if ADMIN_TOKEN and ADMIN_TOKEN.strip():
        # Production environment requires a valid token
        if not token or token != ADMIN_TOKEN:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized. Provide a valid 'token' query parameter."
            )
    # If no ADMIN_TOKEN is set (development), allow without token
    try:
        samples = [
            DrillModel(
                text_catalan="Hola",
                text_tachelhit="ⴰⵣⵓⵍ",
                text_arabic="مرحبا",
                tag="greeting"
            ),
            DrillModel(
                text_catalan="Com et dius?",
                text_tachelhit="ⵎⴰⵏⵉⵙ ⵉⵙⵎ ⵏⵏⴽ?",
                text_arabic="ما اسمك؟",
                tag="introduction"
            ),
            DrillModel(
                text_catalan="Gràcies",
                text_tachelhit="ⵜⴰⵏⵎⵎⵉⵔⵜ",
                text_arabic="شكرا",
                tag="courtesy"
            )
        ]
        added_samples = []
        for sample in samples:
            existing = db.query(DrillModel).filter(
                DrillModel.text_catalan == sample.text_catalan
            ).first()
            if not existing:
                db.add(sample)
                added_samples.append(sample)
        db.commit()
        # Only refresh inserted instances; refreshing a transient one raises
        for sample in added_samples:
            db.refresh(sample)
        added = len(added_samples)
        return {
            "status": "success",
            "added": added,
            "total": db.query(DrillModel).count()
        }
    except Exception as e:
        db.rollback()
        print(f"[DEBUG] Error seeding: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/translation-space-status")
def debug_translation_space_status():
    """
    Check if the Hugging Face translation space is reachable.
    """
    space_url = HUGGINGFACE_TRANSLATION_SPACE_URL
    if not space_url:
        return {
            "status": "not_configured",
            "message": "HUGGINGFACE_TRANSLATION_SPACE_URL not set"
        }
    try:
        resp = requests.get(space_url, timeout=10)
        return {
            "status": "reachable",
            "http_status": resp.status_code,
            "url": space_url
        }
    except Exception as e:
        return {
            "status": "unreachable",
            "error": str(e),
            "url": space_url
        }

@app.get("/debug/spaces")
def debug_spaces():
    """
    Return all configured Hugging Face Space URLs.
    """
    return {
        "huggingface_space_url": os.getenv("HUGGINGFACE_SPACE_URL"),
        "huggingface_image_space_url": os.getenv("HUGGINGFACE_IMAGE_SPACE_URL"),
        "huggingface_asr_space_url": os.getenv("HUGGINGFACE_ASR_SPACE_URL", ASR_SPACE_DEFAULT),
        "huggingface_translation_space_url": HUGGINGFACE_TRANSLATION_SPACE_URL,
        "message": "These are the configured Hugging Face Spaces"
    }

@app.get("/debug/spaces-status")
async def debug_spaces_status():
    """
    Check reachability of each Hugging Face Space.
    """
    import requests  # already imported but safe
    spaces = {
        "huggingface_space_url": os.getenv("HUGGINGFACE_SPACE_URL"),
        "huggingface_image_space_url": os.getenv("HUGGINGFACE_IMAGE_SPACE_URL"),
        "huggingface_asr_space_url": os.getenv("HUGGINGFACE_ASR_SPACE_URL", ASR_SPACE_DEFAULT),
        "huggingface_translation_space_url": HUGGINGFACE_TRANSLATION_SPACE_URL,
    }
    results = {}
    for name, url in spaces.items():
        if not url:
            results[name] = {"status": "not_configured"}
            continue
        try:
            # Some Spaces may block HEAD, use GET with short timeout
            resp = requests.get(url, timeout=10)
            results[name] = {"status": "reachable", "http_status": resp.status_code}
        except Exception as e:
            results[name] = {"status": "unreachable", "error": str(e)}
    return results

# ===================== DATA IMPORT =====================
@app.post("/import-data/")
def import_data(data: dict = Body(...), db: Session = Depends(get_db)):
    """Import drills, tests, and test attempts from exported JSON"""
    try:
        imported = {
            'drills': 0,
            'tests': 0,
            'test_attempts': 0,
            'skipped': 0
        }

        # Import drills
        if 'drills' in data:
            for drill_data in data['drills']:
                # Check if drill already exists
                existing = db.query(DrillModel).filter(DrillModel.id == drill_data['id']).first()
                if existing:
                    imported['skipped'] += 1
                    continue

                drill = DrillModel(
                    id=drill_data['id'],
                    text_catalan=drill_data.get('text_catalan'),
                    text_tachelhit=drill_data.get('text_tachelhit'),
                    text_arabic=drill_data.get('text_arabic'),
                    audio_url=drill_data.get('audio_url'),
                    video_url=drill_data.get('video_url'),
                    image_url=drill_data.get('image_url')
                )
                db.add(drill)
                imported['drills'] += 1

        # Import tests
        if 'tests' in data:
            for test_data in data['tests']:
                existing = db.query(TestModel).filter(TestModel.id == test_data['id']).first()
                if existing:
                    continue

                test = TestModel(**{k: v for k, v in test_data.items() if k != 'date_created'})
                db.add(test)
                imported['tests'] += 1

        # Import test attempts
        if 'test_attempts' in data:
            for attempt_data in data['test_attempts']:
                existing = db.query(TestAttemptModel).filter(TestAttemptModel.id == attempt_data['id']).first()
                if existing:
                    continue

                attempt = TestAttemptModel(**{k: v for k, v in attempt_data.items() if k != 'date_taken'})
                db.add(attempt)
                imported['test_attempts'] += 1

        db.commit()
        return {
            "status": "success",
            "imported": imported
        }

    except Exception as e:
        db.rollback()
        print(f"[IMPORT] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ===================== GLOSSARY =====================

@app.get("/glossary/", response_model=List[GlossaryItem])
def get_glossary(db: Session = Depends(get_db)):
    return db.query(GlossaryItemModel).all()

@app.post("/glossary/", response_model=GlossaryItem)
def create_glossary_item(item: GlossaryItemCreate, db: Session = Depends(get_db)):
    db_item = GlossaryItemModel(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/glossary/{item_id}")
def delete_glossary_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(GlossaryItemModel).filter(GlossaryItemModel.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(db_item)
    db.commit()
    return {"detail": "Deleted"}

# ===================== ASR & CORRECTION =====================

@app.get("/pairs/", response_model=List[DrillPairInfo])
def list_available_pairs(db: Session = Depends(get_db)):
    """
    Returns a list of drills with Tachelhit text that are marked for correction dataset.
    """
    drills = db.query(DrillModel).filter(
        DrillModel.text_tachelhit != None,
        DrillModel.is_correction_dataset == True
    ).all()
    return [
        DrillPairInfo(
            id=drill.id,
            text_tachelhit=drill.text_tachelhit,
            text_catalan=drill.text_catalan
        ) for drill in drills
    ]

@app.post("/transcribe/", response_model=TranscribeResponse)
async def transcribe_audio(
    request: TranscribeRequest,
    db: Session = Depends(get_db)
):
    """
    Calls external Hugging Face ASR Space to process audio.
    """
    audio_url = request.audio_url

    # If audio_url is not provided but we have a cloudinary_path, use it
    if not audio_url and request.cloudinary_path:
        base_url = os.getenv("CLOUDINARY_BASE_URL", "https://res.cloudinary.com/dnx9mqj4p/video/upload/")
        if not base_url.endswith("/"): base_url += "/"
        audio_url = base_url + request.cloudinary_path

    if not audio_url:
        # Try to find the drill to get its audio_url and catalan text if not provided
        # This is a safety fallback
        raise HTTPException(status_code=400, detail="Missing audio_url")

    # Build phrase list from dataset (Include Catalan for semantic matching)
    if request.selected_pair_ids:
        drills = db.query(DrillModel).filter(DrillModel.id.in_(request.selected_pair_ids)).all()
    else:
        # First try to get drills marked for correction dataset
        drills = db.query(DrillModel).filter(DrillModel.is_correction_dataset == True).all()
        if not drills:
            # Fallback to any drill with Tachelhit text (limit to 100)
            drills = db.query(DrillModel).filter(
                DrillModel.text_tachelhit != None,
                DrillModel.text_tachelhit != ''
            ).limit(100).all()

    # Fetch Glossary
    glossary = db.query(GlossaryItemModel).all()
    glossary_data = [{"s": item.word_sound, "c": item.correct_spelling} for item in glossary]

    # Create pairs: { "t": "tachelhit" }
    dataset_pairs = [
        {"t": d.text_tachelhit}
        for d in drills if d.text_tachelhit
    ]

    # Short clips (a word, a short phrase): Gemini measured a 0.19 character error
    # rate on the 2026-10-17 bake-off against 0.76 for the NeMo Space, so it is the
    # engine for clips up to ASR_GEMINI_MAX_SECS (20 s; the bake-off clips went to 18 s). Longer audio keeps the Space.
    # When the drill is known, its variety picks the listener (dialect.py) and its meaning,
    # the speaker's own spelling and the corpus's sentences in that variety guide it.
    variety, meaning, speaker_text, examples = request.variety, None, None, None
    if request.drill_id:
        drill = db.query(DrillModel).filter(DrillModel.id == request.drill_id).first()
        if drill is not None:
            variety = variety or drill.variety
            meaning = drill.text_catalan
            gold = (drill.text_tachelhit or "").strip()
            speaker_text = gold if gold and gold.lower() != "text" else None
            examples = _dialect_examples(db, variety)
    short = await asyncio.to_thread(_transcribe_short_clip_with_gemini, audio_url, variety, meaning, speaker_text, examples)
    if short is not None:
        # Both scripts: the Latin reading (comparable letter by letter with what the speaker typed)
        # and its Tifinagh, «latin · ⵜⵉⴼⵉⵏⴰⵖ».
        latin, tif = (short.get("latin") or "").strip(), (short.get("tifinagh") or "").strip()
        if len(re.sub(r"[^\w]", "", latin or tif)) < 3:
            raise HTTPException(status_code=502, detail="No s'ha entès res de la gravació")
        reading = f"{latin} · {tif}" if latin and tif and latin != tif else (latin or tif)
        return TranscribeResponse(rough_transcription=latin, corrected_transcription=reading, similarity_score=0.0)

    # Call HF Space
    asr_space_url = os.getenv("HUGGINGFACE_ASR_SPACE_URL", ASR_SPACE_DEFAULT)
    if not asr_space_url:
        raise HTTPException(status_code=500, detail="HUGGINGFACE_ASR_SPACE_URL not configured in environment")

    try:
        print(f"[API] Calling ASR Space at {asr_space_url}")
        # hf_predict waits out cold-boot and retries (free Spaces sleep when idle)
        rough = await asyncio.to_thread(
            hf_predict, asr_space_url, handle_file(audio_url), api_name="/predict"
        )

        # Correction layer: apply glossary sound->spelling fixes, then map the
        # rough transcription onto the curated phrase dataset (DeepSeek when
        # DEEPSEEK_API_KEY is set, local fuzzy matching otherwise).
        corrected = rough
        score = 1.0
        if isinstance(rough, str) and rough.strip():
            fixed = apply_glossary(rough, [(g["s"], g["c"]) for g in glossary_data])
            phrases = [p["t"] for p in dataset_pairs]
            try:
                corrected, score = await asyncio.to_thread(
                    get_correction_service().correct_transcription, fixed, phrases
                )
                # Mapping onto the nearest known phrase turned junk into a real-looking
                # sentence (a squirrel clip came back as the video's title). Only accept
                # the mapping when it is actually close; otherwise keep what was heard.
                if score < float(os.getenv("ASR_CORRECTION_MIN_SCORE", "0.6")):
                    corrected = fixed
            except Exception as corr_err:
                print(f"[CORRECTION] Failed, returning rough transcription: {corr_err}")
                corrected, score = fixed, 0.0

        return TranscribeResponse(
            rough_transcription=rough,
            corrected_transcription=corrected,
            similarity_score=score
        )
    except Exception as e:
        print(f"[ASR_SPACE ERROR] {type(e).__name__}: {str(e)}")
        # Try a fallback if handle_file fails
        try:
            client = Client(asr_space_url)
            rough = await asyncio.to_thread(
                client.predict,
                audio_url,
                api_name="/predict"
            )
            return TranscribeResponse(
                rough_transcription=rough,
                corrected_transcription=rough,
                similarity_score=1.0
            )
        except Exception as fallback_e:
            print(f"[ASR_SPACE FALLBACK ERROR] {type(fallback_e).__name__}: {str(fallback_e)}")
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

class ASRService:
    def transcribe(self, audio_url: str) -> str:
        """
        Call the Hugging Face ASR Space to transcribe the given audio URL.
        """
        asr_space_url = os.getenv("HUGGINGFACE_ASR_SPACE_URL", ASR_SPACE_DEFAULT)
        if not asr_space_url:
            raise ValueError("HUGGINGFACE_ASR_SPACE_URL not configured")

        hf_token = os.getenv("HUGGINGFACE_API_KEY")
        try:
            client = Client(asr_space_url, token=hf_token)
            rough = client.predict(
                handle_file(audio_url),
                api_name="/predict"
            )
            return rough
        except Exception as e:
            try:
                client_id = asr_space_url
                if "huggingface.co/spaces/" in asr_space_url:
                    client_id = asr_space_url.split("huggingface.co/spaces/")[-1]
                client = Client(client_id, token=hf_token)
                rough = client.predict(
                    audio_url,
                    api_name="/predict"
                )
                return rough
            except Exception as fallback_e:
                raise Exception(f"Transcription request failed: {str(fallback_e)}")

def get_asr_service():
    return ASRService()

@app.post("/evaluate-dataset/")
async def evaluate_dataset(
    selected_pair_ids: List[int] = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Evaluate ASR performance on all selected audio-text pairs.
    """
    drills = db.query(DrillModel).filter(DrillModel.id.in_(selected_pair_ids)).all()
    results = []

    asr = get_asr_service()

    for drill in drills:
        if not drill.audio_url or not drill.text_tachelhit:
            continue

        try:
            rough = asr.transcribe(drill.audio_url)
            results.append({
                "drill_id": drill.id,
                "expected": drill.text_tachelhit,
                "actual": rough,
                "match": rough.strip().lower() == drill.text_tachelhit.strip().lower()
            })
        except Exception as e:
            results.append({
                "drill_id": drill.id,
                "error": str(e)
            })

    return results

_text_fill_job = {"running": False, "total": 0, "done": 0, "failed": 0, "last": None}


def _run_text_fill(variety: str, limit: int) -> None:
    """Ask the listener for a reading of every recording whose words nobody has written."""
    db = SessionLocal()
    try:
        rows = (db.query(DrillModel)
                .filter(DrillModel.audio_url.isnot(None), DrillModel.audio_url != "")
                .order_by(DrillModel.id.desc()).all())
        todo = [d for d in rows
                if not (d.text_tachelhit or "").strip()
                and not (d.text_tachelhit_suggested or "").strip()][:max(1, limit)]
        _text_fill_job["total"] = len(todo)
        for drill in todo:
            if not _text_fill_job["running"]:
                break
            v = (drill.variety or variety or "").strip().lower()
            if not dialect.profile(v):
                _text_fill_job["failed"] += 1
                continue
            try:
                out = dialect.transcribe(drill.audio_url, v, meaning=drill.text_catalan,
                                         speaker_text=None, examples=[],
                                         max_secs=float(os.getenv("ASR_GEMINI_MAX_SECS", "30")))
            except Exception as e:
                print(f"[TEXT-FILL] drill {drill.id}: {str(e)[:120]}")
                out = None
            if not out or not (out.get("latin") or "").strip():
                _text_fill_job["failed"] += 1
                continue
            drill.text_tachelhit_suggested = out["latin"]
            drill.updated_at = datetime.utcnow()
            db.commit()
            _text_fill_job["done"] += 1
            _text_fill_job["last"] = out["latin"][:60]
        print(f"[TEXT-FILL] drafted {_text_fill_job['done']} of {_text_fill_job['total']} "
              f"({_text_fill_job['failed']} could not be read)")
    except Exception as e:
        print(f"[TEXT-FILL] stopped: {e}")
    finally:
        db.close()
        _text_fill_job["running"] = False


@app.post("/drills/transcribe-missing")
def transcribe_missing_text(variety: str = "tzm", limit: int = 120,
                            _admin: UserModel = Depends(require_admin)):
    """Draft the words of every recording that has none (#189 is blocked on exactly this).

    The reading goes to `text_tachelhit_suggested` and waits for a person in the verification
    queue. The speaker's own field is never touched by a machine — that rule does not bend for a
    hundred recordings any more than it bends for one.
    """
    if _text_fill_job["running"]:
        return {"status": "already_running", **_text_fill_job}
    import threading
    _text_fill_job.update({"running": True, "total": 0, "done": 0, "failed": 0, "last": None})
    threading.Thread(target=_run_text_fill, args=(variety, limit), daemon=True).start()
    return {"status": "started", "variety": variety, "limit": limit}


@app.get("/drills/transcribe-missing/status")
def transcribe_missing_status(db: Session = Depends(get_db)):
    """How the drafting is going, and how many recordings are still mute on paper."""
    waiting = (db.query(DrillModel)
               .filter(DrillModel.audio_url.isnot(None), DrillModel.audio_url != "")
               .filter((DrillModel.text_tachelhit.is_(None)) | (DrillModel.text_tachelhit == ""))
               .count())
    return {**_text_fill_job, "recordings_without_words": waiting}


@app.post("/drills/transcribe-missing/stop")
def transcribe_missing_stop():
    _text_fill_job["running"] = False
    return {"status": "stopping"}


@app.post("/drills/{drill_id}/retranscribe")
async def retranscribe_drill(drill_id: int, variety: Optional[str] = Body(None, embed=True), db: Session = Depends(get_db)):
    """Listen to the drill's recording again with the listener of its variety and write the
    reading to text_tachelhit_suggested (machine output; the speaker's text is never touched).
    `variety` overrides the drill's own for this call."""
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
    source = drill.audio_url or drill.video_url
    if not source:
        raise HTTPException(status_code=400, detail="Aquest drill no té cap gravació")
    # Singing is not speech, and our transcriber does not pretend otherwise gracefully: on the
    # sung cuts it answers with something that reads like a sentence and is not one, and twice it
    # looped on a single word fifty times. A draft like that lands in the verify queue asking a
    # person to judge noise. A sung line's words come from the video -- burned-in lyrics or a
    # subtitle track -- and from nowhere else (owner's ruling, 2026-10-23).
    if "canco" in topics_catalog.parse(getattr(drill, "topics", None)):
        raise HTTPException(
            status_code=400,
            detail="Això és una línia cantada, i el transcriptor no sap cantar. La lletra ha de "
                   "sortir del vídeo mateix: el text sobreimprès o els subtítols.")
    v = (variety or drill.variety or "").strip().lower()
    if not dialect.profile(v):
        raise HTTPException(status_code=400, detail="Cal una varietat coneguda (shi, tzm, tdl, zgh, rif, kab) per triar el transcriptor")
    gold = (drill.text_tachelhit or "").strip()
    speaker_text = gold if gold and gold.lower() != "text" and not re.search(r"[\u2D30-\u2D7F]", gold) else None
    examples = [e for e in _dialect_examples(db, v) if not speaker_text or not e.startswith(speaker_text)]
    out = await asyncio.to_thread(dialect.transcribe, get_media_url(source) if callable(globals().get("get_media_url")) else source, v,
                                  meaning=drill.text_catalan, speaker_text=speaker_text, examples=examples,
                                  max_secs=float(os.getenv("ASR_GEMINI_MAX_SECS", "30")))
    if not out:
        raise HTTPException(status_code=502, detail="No s'ha pogut transcriure la gravació")
    drill.text_tachelhit_suggested = out["latin"]
    drill.updated_at = datetime.utcnow()
    db.commit()
    return {"id": drill.id, "variety": v, **out}


@app.post("/drills/{drill_id}/recut")
def recut_drill_from_source(drill_id: int,
                            start_time: float = Body(..., embed=True),
                            end_time: float = Body(..., embed=True),
                            db: Session = Depends(get_db),
                            user: Optional[UserModel] = Depends(get_current_user)):
    """Cut this sentence's clip again from the ORIGINAL video.

    `trim-audio` and `trim-video` cut the clip we already hold, so a cut the machine made too
    short can never be made longer by them: what was left out is not in the file. This goes back
    to `source_url` and cuts again, which is the only way to recover it.

    The sentence's TEXT is not touched. Moving the cut and changing the words are two different
    decisions and they are taken one at a time.

    A picture that was DRAWN for this sentence is not replaced by a frame grab: illustrations live
    under `tachelhit/images` and frames under `tachelhit/image_segments`, so one that did not come
    from cutting the video was made on purpose and stays.
    """
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
    owner_or_admin(drill, user)
    if not (drill.source_url or "").strip():
        raise HTTPException(status_code=400, detail="Aquesta frase no ve de cap vídeo: no hi ha d'on tornar a tallar.")
    if start_time < 0 or end_time <= start_time:
        raise HTTPException(status_code=400, detail="El tram no té sentit: el final ha d'anar després de l'inici.")
    if end_time - start_time > 120:
        raise HTTPException(status_code=400, detail="Dos minuts és massa per a una frase. Escurça el tram.")
    if not os.getenv("HUGGINGFACE_SPACE_URL"):
        raise HTTPException(status_code=503, detail="Ara mateix no es pot tallar: el servei de vídeo no està configurat.")

    try:
        res = remote_process_and_upload_segment(drill.source_url, start_time, end_time, drill.id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"No s'ha pogut tallar: {str(e)[:160]}")

    drill.video_url = normalize_media_url(res["video_url"])
    was_a_frame = "image_segments" in (drill.image_url or "")
    if res.get("image_url") and (not drill.image_url or was_a_frame):
        drill.image_url = normalize_media_url(res["image_url"])
    drill.video_start_time = start_time
    drill.video_end_time = end_time
    drill.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(drill)
    return {"id": drill.id, "video_url": drill.video_url, "image_url": drill.image_url,
            "video_start_time": drill.video_start_time, "video_end_time": drill.video_end_time,
            "kept_drawing": bool(drill.image_url) and not was_a_frame}


@app.post("/drills/{drill_id}/trim-audio")
def trim_drill_audio(
    drill_id: int,
    start_time: float = Body(..., embed=True),
    end_time: float = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Trims the audio of a drill using MoviePy and uploads the result.
    Plain `def` on purpose (P4.5): download + MoviePy + Cloudinary all block,
    so FastAPI runs this in the threadpool instead of on the event loop.
    """
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill or not drill.audio_url:
        raise HTTPException(status_code=404, detail="Drill or audio not found")
    if start_time < 0 or end_time <= start_time:
        raise HTTPException(status_code=400, detail="Invalid trim range")

    tmp_in_path = None
    tmp_out_path = None
    try:
        from moviepy.audio.io.AudioFileClip import AudioFileClip

        # Download original audio
        response = requests.get(drill.audio_url, stream=True)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_in:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_in.write(chunk)
            tmp_in_path = tmp_in.name

        # Trim audio
        with AudioFileClip(tmp_in_path) as audio:
            trimmed = audio.subclipped(start_time, min(end_time, audio.duration))
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_out:
                tmp_out_path = tmp_out.name
                trimmed.write_audiofile(tmp_out_path, logger=None)

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            tmp_out_path,
            folder="tachelhit/audio",
            public_id=f"audio_trimmed_{drill_id}_{int(datetime.utcnow().timestamp())}",
            resource_type="video"
        )

        url = normalize_media_url(result['secure_url'])
        drill.audio_url = url
        db.commit()

        return {"url": url}

    except Exception as e:
        print(f"[TRIM] Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Temp files are removed on success AND failure
        for p in (tmp_in_path, tmp_out_path):
            if p and os.path.exists(p):
                try: os.unlink(p)
                except OSError: pass

@app.post("/drills/{drill_id}/trim-video")
def trim_drill_video(
    drill_id: int,
    start_time: float = Body(..., embed=True),
    end_time: float = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Trims the video of a drill using MoviePy and uploads the result.
    Plain `def` on purpose (P4.5) — see trim_drill_audio.
    """
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill or not drill.video_url:
        raise HTTPException(status_code=404, detail="Drill or video not found")
    if start_time < 0 or end_time <= start_time:
        raise HTTPException(status_code=400, detail="Invalid trim range")

    tmp_in_path = None
    tmp_out_path = None
    try:
        from moviepy.video.io.VideoFileClip import VideoFileClip

        # Download original video
        response = requests.get(drill.video_url, stream=True)
        response.raise_for_status()

        # Extension detection
        ext = ".mp4"
        if "webm" in drill.video_url: ext = ".webm"
        elif "mov" in drill.video_url: ext = ".mov"

        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_in:
            for chunk in response.iter_content(chunk_size=8192):
                tmp_in.write(chunk)
            tmp_in_path = tmp_in.name

        # Trim video
        with VideoFileClip(tmp_in_path) as video:
            trimmed = video.subclipped(start_time, min(end_time, video.duration))
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_out:
                tmp_out_path = tmp_out.name
                # We use a fast preset and avoid heavy encoding if possible
                trimmed.write_videofile(tmp_out_path, codec="libx264", audio_codec="aac", logger=None)

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            tmp_out_path,
            folder="tachelhit/video",
            public_id=f"video_trimmed_{drill_id}_{int(datetime.utcnow().timestamp())}",
            resource_type="video"
        )

        url = normalize_media_url(result['secure_url'])
        drill.video_url = url
        db.commit()

        return {"url": url}

    except Exception as e:
        print(f"[TRIM VIDEO] Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Temp files are removed on success AND failure
        for p in (tmp_in_path, tmp_out_path):
            if p and os.path.exists(p):
                try: os.unlink(p)
                except OSError: pass

# ===================== SRT IMPORT =====================
@app.post("/srt/import", response_model=SrtImportResponse)
def import_srt_content(request: SrtImportRequest, db: Session = Depends(get_db),
                       user: Optional[UserModel] = Depends(get_current_user)):
    """
    Import SRT subtitle content and create drills for each segment.
    Each drill will have a video URL with timestamp for the specific segment.
    """
    try:
        print(f"[SRT IMPORT] Importing SRT content for video: {request.video_url}")
        print(f"[SRT IMPORT] SRT content length: {len(request.srt_content)} characters")

        # Parse SRT content
        segments = parse_srt_content(request.srt_content)
        print(f"[SRT IMPORT] Parsed {len(segments)} segments")

        drill_ids = []
        created_drills = []

        # Create a drill for each segment
        for i, segment in enumerate(segments):
            try:
                # Create YouTube URL with timestamp
                youtube_url = create_youtube_url_with_timestamp(request.video_url, segment["start_time"])

                # Create drill with the segment text as Catalan text
                # The SRT content is in Catalan (from the YouTube Catalan translator)
                db_drill = DrillModel(
                    text_catalan=segment["text"],
                    tag=request.tag,
                    author=request.author,
                    video_url=youtube_url,
                    video_start_time=segment["start_time"],
                    video_end_time=segment["end_time"]
                )

                db.add(db_drill)
                db.flush()  # Get the ID without committing

                # Generate Arabic translation
                try:
                    db_drill.text_arabic = translator_ca_to_ar.translate(segment["text"])
                except Exception as trans_e:
                    print(f"[SRT IMPORT] Translation error for segment {i+1}: {trans_e}")

                # Generate TTS audio
                try:
                    tts_url = generate_catalan_tts(segment["text"], db_drill.id)
                    db_drill.audio_tts_url = tts_url
                except Exception as tts_e:
                    print(f"[SRT IMPORT] TTS error for segment {i+1}: {tts_e}")

                drill_ids.append(db_drill.id)
                created_drills.append(db_drill)

                print(f"[SRT IMPORT] Created drill {db_drill.id} for segment {i+1}: '{segment['text'][:50]}...'")

            except Exception as segment_e:
                print(f"[SRT IMPORT] Error creating drill for segment {i+1}: {segment_e}")
                continue

        # Commit all drills
        db.commit()

        # Create test if requested
        test_id = None
        if request.create_test and drill_ids:
            try:
                test_title = request.test_title or f"SRT Import - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
                test_description = request.test_description or f"Test created from SRT import with {len(drill_ids)} segments"

                db_test = TestModel(
                    title=test_title,
                    description=test_description,
                    drill_ids=",".join(str(did) for did in drill_ids),
                    question_type="text_input",
                    hint_level="none",
                    created_by_user_id=user.id if user else None,
                )
                db.add(db_test)
                db.commit()
                db.refresh(db_test)
                test_id = db_test.id

                print(f"[SRT IMPORT] Created test {test_id} with {len(drill_ids)} drills")
            except Exception as test_e:
                print(f"[SRT IMPORT] Error creating test: {test_e}")

        return SrtImportResponse(
            success=True,
            message=f"Successfully imported {len(drill_ids)} segments from SRT",
            drill_count=len(drill_ids),
            drill_ids=drill_ids,
            test_id=test_id,
            segments=segments
        )

    except Exception as e:
        db.rollback()
        print(f"[SRT IMPORT] Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"SRT import failed: {str(e)}")

# ===================== BULK VIDEO URL UPDATE =====================
@app.post("/drills/bulk-update-video-url", response_model=BulkVideoUrlUpdateResponse)
def bulk_update_video_url(request: BulkVideoUrlUpdateRequest, db: Session = Depends(get_db)):
    """
    Bulk update video URLs for multiple drills.
    For each drill, creates a proper YouTube URL with timestamp using video_start_time.
    """
    try:
        print(f"[BULK VIDEO URL] Updating video URLs for {len(request.drill_ids)} drills")
        print(f"[BULK VIDEO URL] Base video URL: {request.base_video_url}")

        updated_count = 0
        failed_ids = []

        for drill_id in request.drill_ids:
            try:
                # Get the drill
                drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
                if not drill:
                    print(f"[BULK VIDEO URL] Drill {drill_id} not found")
                    failed_ids.append(drill_id)
                    continue

                # Create the YouTube URL with timestamp if requested
                if request.update_timestamps and drill.video_start_time is not None:
                    youtube_url = create_youtube_url_with_timestamp(
                        request.base_video_url,
                        drill.video_start_time
                    )
                else:
                    # Just use the base URL without timestamp
                    youtube_url = request.base_video_url

                # Update the drill's video_url
                drill.video_url = youtube_url
                db.add(drill)

                print(f"[BULK VIDEO URL] Updated drill {drill_id}: {youtube_url}")
                updated_count += 1

            except Exception as drill_error:
                print(f"[BULK VIDEO URL] Error updating drill {drill_id}: {drill_error}")
                failed_ids.append(drill_id)
                continue

        # Commit all changes
        db.commit()

        message = f"Successfully updated {updated_count} drills"
        if failed_ids:
            message += f", failed to update {len(failed_ids)} drills"

        return BulkVideoUrlUpdateResponse(
            success=True,
            message=message,
            updated_count=updated_count,
            failed_ids=failed_ids
        )

    except Exception as e:
        db.rollback()
        print(f"[BULK VIDEO URL] Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Bulk video URL update failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("=" * 80)
    print("Starting Tachelhit Drills backend server")
    print(f"Listening on http://0.0.0.0:8000")
    print("=" * 80)
    # Nota: No se ha desplegado a Render automáticamente; se necesita push a GitHub.
    uvicorn.run(app, host="0.0.0.0", port=8000)
