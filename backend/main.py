# INFO: Project: Tachelhit Drills. Feature: ASR, Correction, Translation, Video Processing. Status: Active.
import asyncio
import os
import json
import traceback
import tempfile
import shutil
import yt_dlp
from datetime import datetime, timedelta
from urllib.parse import quote
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Body, Form, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Optional, List, Dict
import hashlib
import re
import secrets
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import requests
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from gradio_client import Client, handle_file

from deep_translator import GoogleTranslator

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

from models import Base, Drill as DrillModel, Test as TestModel, TestAttempt as TestAttemptModel, YouTubeShort as YouTubeShortModel, VideoProcessingJob as VideoProcessingJobModel, VideoSegment as VideoSegmentModel, GlossaryItem as GlossaryItemModel, DrillReview as DrillReviewModel, User as UserModel, ReviewLog as ReviewLogModel  # ← Alias for ORM models
from schemas import DrillCreate, DrillUpdate, Drill, TestCreate, TestUpdate, Test, TestAttemptCreate, TestAttempt, YouTubeShortCreate, YouTubeShort, VideoProcessingJobCreate, VideoProcessingJob, VideoSegmentCreate, VideoSegment, TranscribeRequest, TranscribeResponse, TranslateRequest, TranslateResponse, DrillPairInfo, GlossaryItem, GlossaryItemCreate, SrtImportRequest, SrtImportResponse, SrtSegment, BulkVideoUrlUpdateRequest, BulkVideoUrlUpdateResponse  # ← Pydantic schemas
from correction_service import get_correction_service
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
HUGGINGFACE_TRANSLATION_SPACE_URL = os.getenv("HUGGINGFACE_TRANSLATION_SPACE_URL", "https://huggingface.co/spaces/josepabloucr/Finetuned-Quantized-NLLB")
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

    # If custom space URL is provided, use it
    if HUGGINGFACE_TRANSLATION_SPACE_URL:
        try:
            # Use the official Gradio Client for robust communication
            # Remove /translate suffix if present as Client expects the base URL
            space_url = HUGGINGFACE_TRANSLATION_SPACE_URL.split('/translate')[0].rstrip('/')

            # Extract just the repository ID if it's a full huggingface.co URL
            client_id = space_url
            if "huggingface.co/spaces/" in space_url:
                client_id = space_url.split("huggingface.co/spaces/")[-1]

            print(f"[TRANSLATE] Connecting to Gradio Space: {client_id}")

            api_token = os.getenv("HUGGINGFACE_API_KEY")
            import httpx
            # A sleeping free-tier Space wakes and loads the model on first
            # request; the default httpx read timeout aborts mid-wake, so give
            # it a long one and retry once.
            client = Client(client_id, token=api_token,
                            httpx_kwargs={"timeout": httpx.Timeout(180.0, connect=30.0)})
            # The app.py has fn=translate_text with inputs [text, src_lang, tgt_lang]
            result = None
            for attempt in (1, 2):
                try:
                    result = client.predict(
                        text,
                        src_lang,
                        tgt_lang,
                        237,
                        4,
                        1.0,
                        api_name="/predict"
                    )
                    break
                except Exception as retry_err:
                    print(f"[TRANSLATE] Space attempt {attempt} failed: {retry_err}")
                    if attempt == 2:
                        raise

            # The Space returns "Tifinagh: ...\nLatín: ..." for ber_Tfng
            translation = str(result)
            print(f"[TRANSLATE] Success (Gradio Space): '{text[:30]}...' -> '{translation[:30]}...'")
            return translation

        except Exception as e:
            print(f"[TRANSLATE] Gradio Space error details: {e}")
            import traceback
            traceback.print_exc()
            print(f"[TRANSLATE] Falling back to Inference API.")

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

def generate_tachelhit_tts_hf(text: str, drill_id: int) -> str:
    """
    Generate Tachelhit TTS using a Hugging Face Space (HUGGINGFACE_TTS_SPACE_URL,
    default Tamazight-NLP/TTS).
    """
    try:
        from gradio_client import Client
        # Accept either a "user/space" id or a full huggingface.co/spaces URL.
        tts_space = HUGGINGFACE_TTS_SPACE_URL
        if "huggingface.co/spaces/" in tts_space:
            tts_space = tts_space.split("huggingface.co/spaces/")[-1].rstrip("/")
        print(f"[TACHELHIT TTS] Using Space: {tts_space}")
        client = Client(tts_space, token=os.getenv("HUGGINGFACE_API_KEY"))

        # predict(text, variant, speaker, split_sentences, speaker_wav, voice_cv_model, api_name="/predict")
        result_path = client.predict(
            text,
            "shi",
            "yan",
            False,
            None,
            "freevc24",
            api_name="/predict"
        )
        
        timestamp = int(datetime.utcnow().timestamp())
        filename = f"tachelhit_tts_{drill_id}_{timestamp}.wav"
        
        use_cloudinary = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))
        
        if use_cloudinary:
            result = cloudinary.uploader.upload(
                result_path,
                folder="tachelhit/tts",
                public_id=f"tachelhit_tts_{drill_id}_{timestamp}",
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

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs ON STARTUP
    print("[INIT] Startup lifespan events...")

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

    yield
    # This runs ON SHUTDOWN
    print("[INIT] Shutdown lifespan events...")

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

app = FastAPI(title="Tachelhit Drills API", lifespan=lifespan)

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print(f"[GLOBAL ERROR] {type(exc).__name__}: {str(exc)}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}", "type": type(exc).__name__},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*"
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"[VALIDATION ERROR] {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
        headers={"Access-Control-Allow-Origin": "*"}
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

class TtsRequest(BaseModel):
    text: str
    drill_id: Optional[int] = 0

@app.post("/tts/tachelhit")
@app.post("/tts/tachelhit/")
async def tachelhit_tts_endpoint(request: TtsRequest):
    """
    Generate Tachelhit TTS for given Tifinagh text.
    """
    if not request.text:
        raise HTTPException(status_code=400, detail="Text is required")
    try:
        url = await asyncio.to_thread(generate_tachelhit_tts_hf, request.text, request.drill_id or 0)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    """Resolve the requesting user from the X-User-Token header (None = anonymous)."""
    token = (request.headers.get("x-user-token") or "").strip()
    if not token:
        return None
    return db.query(UserModel).filter(UserModel.token == _hash_token(token)).first()

# ===================== CRUD =====================
@app.get("/drills/", response_model=list[Drill])
def get_drills(tag: Optional[str] = None, author: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        query = db.query(DrillModel)

        if tag:
            # Simple substring match for tags (since they can be comma-separated)
            query = query.filter(DrillModel.tag.ilike(f"%{tag}%"))

        if author:
            query = query.filter(DrillModel.author.ilike(f"%{author}%"))

        drills = query.order_by(DrillModel.date_created.desc()).all()
        print(f"[API] GET /drills/ (tag={tag}, author={author}) returning {len(drills)} drills")
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
    except Exception as e:
        print(f"[API] ERROR in GET /drills/: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/drills/", response_model=Drill)
def create_drill(drill: DrillCreate = None, db: Session = Depends(get_db),
                 user: Optional[UserModel] = Depends(get_current_user)):
    try:
        # If no data is provided, create an empty drill
        if drill is None:
            db_drill = DrillModel()
        else:
            # Create drill with provided data
            drill_data = drill.model_dump(exclude_unset=True)
            db_drill = DrillModel(**drill_data)

        # Contributor attribution
        if user:
            db_drill.created_by_user_id = user.id
            if not db_drill.author:
                db_drill.author = user.display_name or user.username

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
def update_drill(drill_id: int, update_data: DrillUpdate, db: Session = Depends(get_db)):
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")

    update_dict = update_data.model_dump(exclude_unset=True)

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

    db.commit()
    db.refresh(drill)
    return drill

@app.delete("/drills/{drill_id}")
def delete_drill(drill_id: int, db: Session = Depends(get_db)):
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")
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
        if use_ai:
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
                    client.predict,
                    final_prompt,
                    api_name="/generate"
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

            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
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
@app.get("/tests/", response_model=list[Test])
def get_tests(db: Session = Depends(get_db)):
    return db.query(TestModel).order_by(TestModel.date_created.desc()).all()

@app.get("/tests/{test_id}", response_model=Test)
def get_test(test_id: int, db: Session = Depends(get_db)):
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test

@app.post("/tests/", response_model=Test)
def create_test(test: TestCreate, db: Session = Depends(get_db)):
    db_test = TestModel(**test.model_dump())
    db.add(db_test)
    db.commit()
    db.refresh(db_test)
    return db_test

@app.put("/tests/{test_id}", response_model=Test)
def update_test(test_id: int, update_data: TestUpdate, db: Session = Depends(get_db)):
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(test, key, value)

    db.commit()
    db.refresh(test)
    return test

@app.delete("/tests/{test_id}")
def delete_test(test_id: int, db: Session = Depends(get_db)):
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    db.delete(test)
    db.commit()
    return {"detail": "Deleted"}

# ===================== TEST ATTEMPT CRUD =====================
@app.get("/test-attempts/", response_model=list[TestAttempt])
def get_test_attempts(test_id: int = None, db: Session = Depends(get_db)):
    query = db.query(TestAttemptModel)
    if test_id:
        query = query.filter(TestAttemptModel.test_id == test_id)
    return query.order_by(TestAttemptModel.date_taken.desc()).all()

@app.post("/test-attempts/", response_model=TestAttempt)
def create_test_attempt(attempt: TestAttemptCreate, db: Session = Depends(get_db)):
    db_attempt = TestAttemptModel(**attempt.model_dump())
    db.add(db_attempt)
    db.commit()
    db.refresh(db_attempt)
    return db_attempt

# ===================== TEST STATISTICS =====================
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

def background_video_vault(job_type: str, item_id: int, payload_data: list):
    """
    Background worker. Now uploads the LOCALLY downloaded file from Gradio Client.
    """
    db = SessionLocal()
    try:
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

        # Cleanup the local temp file from Gradio Client
        if os.path.exists(local_video_path):
            os.remove(local_video_path)

    except Exception as e:
        print(f"[WORKER] ❌ Task Failed: {str(e)}")
        # Print full traceback to logs for debugging
        traceback.print_exc()
    finally:
        db.close()

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

    # 🚀 Start background task and return immediately
    background_tasks.add_task(background_video_vault, "short", drill_id, payload_data)

    return {"status": "processing", "message": "Video generation started. It will appear in Cloudinary shortly."}
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
    background_tasks.add_task(background_video_vault, "demo", test_id, payload_data)

    return {"status": "processing", "message": "Demo video is being generated. This may take a few minutes."}

@app.get("/shorts/", response_model=list[YouTubeShort])
def get_shorts(db: Session = Depends(get_db)):
    return db.query(YouTubeShortModel).order_by(YouTubeShortModel.date_created.desc()).all()

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

from video_utils import get_video_metadata, get_video_segments, process_and_upload_segment, remote_process_and_upload_segment, get_yt_dlp_cookie_file, download_video_to_dir, process_and_upload_audio_segment, is_audio_file

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

async def process_video_analysis_task(job_id: int, video_path: str, tmp_dir: str, language: Optional[str] = None):
    """
    Background task to extract audio, upload to Cloudinary, call ASR Space, and update job.
    `language` is an optional Whisper language hint forwarded to the ASR Space.
    """
    db = SessionLocal()
    try:
        job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
        if not job: return

        job.status = "IN_PROGRESS"
        db.commit()

        # 3. Call ASR Space (Direct Proxy)
        asr_space_url = os.getenv("HUGGINGFACE_ASR_SPACE_URL", "https://huggingface.co/spaces/Tamazight-NLP/ASR")
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
                for seg in segments:
                    text = seg.get("text") or ""
                    for g in glossary:
                        if g.word_sound:
                            text = text.replace(g.word_sound, g.correct_spelling)
                    seg["text"] = text

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

    # Auto-pipeline jobs record their created drill ids in processing_log
    drills_created = None
    if job.processing_log:
        try:
            log = json.loads(job.processing_log)
            if isinstance(log, dict):
                drills_created = log.get("drills_created")
        except (ValueError, TypeError):
            pass

    return {
        "id": job.id,
        "status": job.status,
        "error_message": job.error_message,
        "segments": segments,
        "drills_created": drills_created
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
                                    lyrics: Optional[str] = None, generate_reels: bool = False):
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

        # Phase 1: transcription (skipped when platform subtitles already gave segments)
        if not has_segments:
            job.status = "TRANSCRIBING"
            db.commit()
            await process_video_analysis_task(job_id, video_path, tmp_dir, language)
            db.expire_all()
            job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
            if not job or job.status != "COMPLETED":
                return  # ASR failed; its task already recorded the error

        segments = [{
            "start": s.segment_start_time,
            "end": s.segment_end_time,
            "text": s.text_original
        } for s in job.segments]

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
            segments = _align_lyrics_lines(segments, lyrics)
            apply_correction = False

        # Phase 2: correction layer (Tachelhit-ish sources only)
        if apply_correction and effective_source in ("shi", "ber"):
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
                if text:
                    try:
                        corrected, _ = await asyncio.to_thread(svc.correct_transcription, text, phrases)
                        seg["text"] = corrected
                    except Exception as e:
                        print(f"[AUTO] Correction failed for a segment: {e}")

        # Phase 3: translate into every drill language the source isn't
        job.status = "TRANSLATING"
        db.commit()
        for seg in segments:
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            for tgt, field in TRANSLATE_TARGET_FIELDS.items():
                if LANGUAGE_CODE_MAP.get(tgt) == src_name:
                    continue
                try:
                    seg[field] = await asyncio.to_thread(
                        translate_with_hf, text, src_name, LANGUAGE_CODE_MAP[tgt]
                    )
                except Exception as e:
                    print(f"[AUTO] Translation ({tgt}) failed for a segment: {e}")

        # Phase 4: create drills with clipped media
        job.status = "CREATING_DRILLS"
        db.commit()
        drills_created = []
        audio_src = is_audio_file(video_path)
        for seg in segments:
            original_text = seg.get("text")
            drill_tachelhit = seg.get("text_tachelhit") or (original_text if effective_source in ("shi", "ber") else None)
            drill_arabic = seg.get("text_arabic") or (original_text if effective_source == "ar" else None)

            db_drill = DrillModel(
                text_catalan=seg.get("text_catalan"),
                text_tachelhit=drill_tachelhit,
                text_arabic=drill_arabic,
                tag=tag or "auto_capture",
                author="Auto Capture",
                source_url=url
            )
            db.add(db_drill)
            db.commit()
            db.refresh(db_drill)
            try:
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
                drills_created.append(db_drill.id)
            except Exception as e:
                print(f"[AUTO] Media clipping failed for a segment: {e}")
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
        job.processing_log = json.dumps({"drills_created": drills_created})
        db.commit()
        print(f"[AUTO] Job {job_id}: created {len(drills_created)} drills (reels={generate_reels}).")

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
                    text_original=seg["text"]
                ))
            db.commit()

        background_tasks.add_task(
            auto_drills_pipeline_task,
            job.id, url, video_path, tmp_dir,
            lang_to_use or language, tag, bool(apply_correction), bool(segments),
            lyrics, bool(generate_reels)
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
            fixed = text
            for g in glossary:
                if g.word_sound:
                    fixed = fixed.replace(g.word_sound, g.correct_spelling)
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

def _align_lyrics_lines(segments: List[Dict], lyrics: str) -> List[Dict]:
    """
    Swap ASR-guessed segment text for real lyric lines while keeping the ASR
    timestamps (ASR hears sung vocals poorly but times them well). Each
    segment gets the best fuzzy-matching lyric line near its proportionally
    expected position; the original ASR guess is preserved in text_asr.
    """
    import difflib

    lines = [l.strip() for l in (lyrics or "").splitlines() if l.strip()]
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
            score = difflib.SequenceMatcher(None, asr_text, lines[j].lower()).ratio()
            if j in used:  # prefer lines not already claimed
                score -= 0.15
            if score > best_score:
                best_idx, best_score = j, score
        used.add(best_idx)
        seg["text_asr"] = seg.get("text")
        seg["text"] = lines[best_idx]
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
    target_langs: Optional[List[str]] = Body(None)
):
    """
    Translate a list of video segments using the fine-tuned NLLB Hugging Face
    Space (Google Translate has no Tachelhit/Tamazight support). By default
    translates to Catalan; pass target_langs (subset of ca/ar/shi) to fill
    several drill languages in one call. Targets equal to the source language
    are skipped.
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
                    field = TRANSLATE_TARGET_FIELDS[tgt]
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

                db_drill = DrillModel(
                    text_catalan=seg.get("text_catalan"),
                    text_tachelhit=drill_tachelhit,
                    text_arabic=drill_arabic,
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

                db_drill = DrillModel(
                    text_catalan=seg.get("text_catalan"),
                    text_tachelhit=drill_tachelhit,
                    text_arabic=drill_arabic,
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

@app.post("/users/register")
def register_user(
    request: Request,
    username: str = Body(..., embed=True),
    display_name: Optional[str] = Body(None, embed=True),
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
        token=_hash_token(raw_token)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"username": user.username, "display_name": user.display_name, "token": raw_token}

@app.get("/users/me")
def get_me(user: Optional[UserModel] = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Missing or invalid X-User-Token")
    drills_contributed = db.query(DrillModel).filter(DrillModel.created_by_user_id == user.id).count()
    cards_learning = db.query(DrillReviewModel).filter(DrillReviewModel.user_id == user.id).count()
    return {
        "username": user.username,
        "display_name": user.display_name,
        "date_created": user.date_created.isoformat(),
        "drills_contributed": drills_contributed,
        "cards_learning": cards_learning
    }

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

# ===================== CORPUS (documentation & research) =====================

CORPUS_EXPORT_FIELDS = [
    "id", "date_created", "tag", "author", "speaker", "variety", "region",
    "license", "source_url", "verified", "text_catalan", "text_tachelhit",
    "text_tachelhit_latin", "text_arabic", "audio_url", "audio_tts_url",
    "video_url", "image_url", "video_start_time", "video_end_time"
]

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
    query = db.query(DrillModel)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            DrillModel.text_tachelhit.ilike(like),
            DrillModel.text_tachelhit_latin.ilike(like),
            DrillModel.text_catalan.ilike(like),
            DrillModel.text_arabic.ilike(like),
        ))
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
def corpus_flywheel(verified_only: bool = False, db: Session = Depends(get_db)):
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
    return {"count": len(pairs), "pairs": pairs}

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

# ===================== PRONUNCIATION CHECK =====================

def _normalize_for_comparison(text: str) -> str:
    """Lowercase, strip punctuation/extra whitespace for fuzzy comparison."""
    cleaned = re.sub(r"[^\w\sⴰ-⵿]", "", (text or "").lower(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", cleaned).strip()

@app.post("/pronunciation/check")
async def pronunciation_check(
    drill_id: int = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Pronunciation feedback: transcribe the user's recording with the ASR
    Space and fuzzy-compare it against the drill's Tachelhit text (after
    glossary sound->spelling normalization). Returns what was heard and a
    0-1 similarity score. Nothing is stored.
    """
    import difflib

    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill or not drill.text_tachelhit:
        raise HTTPException(status_code=404, detail="Drill not found or has no Tachelhit text")
    target = drill.text_tachelhit

    suffix = os.path.splitext(os.path.basename(audio.filename or ""))[1] or ".webm"
    tmp_path = None
    try:
        content = await audio.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        asr_space_url = os.getenv("HUGGINGFACE_ASR_SPACE_URL", "https://huggingface.co/spaces/Tamazight-NLP/ASR")
        client_id = asr_space_url
        if "huggingface.co/spaces/" in asr_space_url:
            client_id = asr_space_url.split("huggingface.co/spaces/")[-1]
        client = Client(client_id, token=os.getenv("HUGGINGFACE_API_KEY"))
        rough = await asyncio.to_thread(client.predict, handle_file(tmp_path), api_name="/predict")
        heard = str(rough or "").strip()

        # Glossary normalization so known sound->spelling quirks don't penalize
        fixed = heard
        for g in db.query(GlossaryItemModel).all():
            if g.word_sound:
                fixed = fixed.replace(g.word_sound, g.correct_spelling)

        score = difflib.SequenceMatcher(
            None, _normalize_for_comparison(fixed), _normalize_for_comparison(target)
        ).ratio()

        return {
            "drill_id": drill_id,
            "target": target,
            "heard": fixed,
            "score": round(score, 3)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[PRONUNCIATION] Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Pronunciation check failed: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except OSError: pass

# ===================== SPACED REPETITION (SRS) =====================
# SM-2 style scheduling. Grades: 0=again, 1=hard, 2=good, 3=easy.

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
        seen = db.query(DrillReviewModel.drill_id).filter(DrillReviewModel.user_id == uid)
        new_drills = (
            db.query(DrillModel)
            .filter(~DrillModel.id.in_(seen))
            .order_by(DrillModel.date_created.desc())
            .limit(limit - len(drills))
            .all()
        )
        drills.extend(new_drills)
    return drills

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
    now = datetime.utcnow()
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
    db.add(ReviewLogModel(drill_id=drill_id, user_id=uid, grade=grade, reviewed_at=now))
    db.commit()
    db.refresh(review)
    return {
        "drill_id": drill_id,
        "next_due": review.due_date.isoformat(),
        "interval_days": round(review.interval_days, 3),
        "ease": round(review.ease, 2),
        "repetitions": review.repetitions
    }

@app.get("/reviews/streak")
def review_streak(db: Session = Depends(get_db),
                  user: Optional[UserModel] = Depends(get_current_user)):
    """Daily streak and activity counts for the requesting user."""
    uid = user.id if user else None
    rows = db.query(ReviewLogModel.reviewed_at).filter(ReviewLogModel.user_id == uid).all()
    days = {r[0].date() for r in rows}
    today = datetime.utcnow().date()

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
        "reviews_today": sum(1 for r in rows if r[0].date() == today),
        "reviews_week": sum(1 for r in rows if r[0].date() >= week_ago),
        "active_days": len(days),
    }

@app.get("/reviews/stats")
def review_stats(db: Session = Depends(get_db),
                 user: Optional[UserModel] = Depends(get_current_user)):
    """Counts for the home-screen review badge, scoped to the requesting user."""
    uid = user.id if user else None
    now = datetime.utcnow()
    total = db.query(DrillModel).count()
    tracked = db.query(DrillReviewModel).filter(DrillReviewModel.user_id == uid).count()
    due = db.query(DrillReviewModel).filter(
        DrillReviewModel.user_id == uid, DrillReviewModel.due_date <= now
    ).count()
    return {
        "total_drills": total,
        "new": max(0, total - tracked),
        "due": due,
        "learning": tracked
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
        "huggingface_asr_space_url": os.getenv("HUGGINGFACE_ASR_SPACE_URL", "https://huggingface.co/spaces/Tamazight-NLP/ASR"),
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
        "huggingface_asr_space_url": os.getenv("HUGGINGFACE_ASR_SPACE_URL", "https://huggingface.co/spaces/josepabloucr/ASR"),
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

    # Call HF Space
    asr_space_url = os.getenv("HUGGINGFACE_ASR_SPACE_URL", "https://huggingface.co/spaces/Tamazight-NLP/ASR")
    if not asr_space_url:
        raise HTTPException(status_code=500, detail="HUGGINGFACE_ASR_SPACE_URL not configured in environment")

    try:
        client_id = asr_space_url
        if "huggingface.co/spaces/" in asr_space_url:
            client_id = asr_space_url.split("huggingface.co/spaces/")[-1]

        print(f"[API] Calling ASR Space at {client_id}")
        hf_token = os.getenv("HUGGINGFACE_API_KEY")
        client = Client(client_id, token=hf_token)

        # For Tamazight-NLP/ASR, we use /predict which takes the audio URL using handle_file
        # Note: If it's a URL, handle_file might work or we can pass the URL string directly if the space accepts it
        # Actually, gradio_client allows passing the URL string for Audio inputs.

        rough = await asyncio.to_thread(
            client.predict,
            handle_file(audio_url),
            api_name="/predict"
        )

        # Correction layer: apply glossary sound->spelling fixes, then map the
        # rough transcription onto the curated phrase dataset (DeepSeek when
        # DEEPSEEK_API_KEY is set, local fuzzy matching otherwise).
        corrected = rough
        score = 1.0
        if isinstance(rough, str) and rough.strip():
            fixed = rough
            for g in glossary_data:
                if g["s"]:
                    fixed = fixed.replace(g["s"], g["c"])
            phrases = [p["t"] for p in dataset_pairs]
            try:
                corrected, score = await asyncio.to_thread(
                    get_correction_service().correct_transcription, fixed, phrases
                )
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
        asr_space_url = os.getenv("HUGGINGFACE_ASR_SPACE_URL", "https://huggingface.co/spaces/josepabloucr/ASR")
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

@app.post("/drills/{drill_id}/trim-audio")
async def trim_drill_audio(
    drill_id: int,
    start_time: float = Body(..., embed=True),
    end_time: float = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Trims the audio of a drill using MoviePy and uploads the result.
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
async def trim_drill_video(
    drill_id: int,
    start_time: float = Body(..., embed=True),
    end_time: float = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Trims the video of a drill using MoviePy and uploads the result.
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
def import_srt_content(request: SrtImportRequest, db: Session = Depends(get_db)):
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
                    hint_level="none"
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
