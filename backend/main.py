# INFO: Project: Tachelhit Drills. Feature: ASR, Correction, Translation, Video Processing. Status: Active.
import asyncio
import os
import json
import traceback
import tempfile
import shutil
import yt_dlp
from datetime import datetime
from urllib.parse import quote
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Body, BackgroundTasks
from typing import Optional, List, Dict
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

from models import Base, Drill as DrillModel, Test as TestModel, TestAttempt as TestAttemptModel, YouTubeShort as YouTubeShortModel, VideoProcessingJob as VideoProcessingJobModel, VideoSegment as VideoSegmentModel, GlossaryItem as GlossaryItemModel  # ← Alias for ORM models
from schemas import DrillCreate, DrillUpdate, Drill, TestCreate, TestUpdate, Test, TestAttemptCreate, TestAttempt, YouTubeShortCreate, YouTubeShort, VideoProcessingJobCreate, VideoProcessingJob, VideoSegmentCreate, VideoSegment, TranscribeRequest, TranscribeResponse, TranslateRequest, TranslateResponse, DrillPairInfo, GlossaryItem, GlossaryItemCreate, SrtImportRequest, SrtImportResponse, SrtSegment  # ← Pydantic schemas
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
            client = Client(client_id, token=api_token)
            # The app.py has fn=translate_text with inputs [text, src_lang, tgt_lang]
            result = client.predict(
                text,
                src_lang,
                tgt_lang,
                237,
                4,
                1.0,
                api_name="/predict"
            )
            
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
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "dX9JkRJYfaRQUZdi6tKsF1TfJT44HnZMAPu2RyA4vt0JyRbzmdiVYGgW")
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

# Database configuration - handle both SQLite and PostgreSQL
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL (from Render or other services)
    engine = create_engine(DATABASE_URL)

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

# CORS configuration - allow frontend URL
allowed_origins_base = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:4173", # Vite default preview server port
    "http://localhost:3000",
    "https://tachelhit-drills.vercel.app",        # Production URL (without www)
    "https://tachelhit-drills.vercel.app/",       # Production URL (with trailing slash)
    "https://www.tachelhit-drills.vercel.app",    # Production URL with www
    "https://www.tachelhit-drills.vercel.app/",   # Production URL with www and slash
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

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
def create_drill(drill: DrillCreate = None, db: Session = Depends(get_db)):
    try:
        # If no data is provided, create an empty drill
        if drill is None:
            db_drill = DrillModel()
        else:
            # Create drill with provided data
            drill_data = drill.model_dump(exclude_unset=True)
            db_drill = DrillModel(**drill_data)
        
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

    # Delete video file
    try:
        video_path = f"media/{short.video_path.replace('/media/', '')}"
        if os.path.exists(video_path):
            os.remove(video_path)
    except Exception as e:
        print(f"[API] Error deleting video file: {e}")

    db.delete(short)
    db.commit()
    return {"detail": "Deleted"}

# ===================== VIDEO PROCESSING =====================

# Placeholder for background task that would offload to external service
async def process_video_background_task(job_id: int, source_url: Optional[str], source_filepath: Optional[str], db_session: Session):
    # In a real scenario, this function would:
    # 1. Update job status to IN_PROGRESS
    # 2. Call external services (serverless functions) for:
    #    a. Video download (if YouTube URL) from source_url
    #    b. Storing the video in a temporary location.
    # 3. Update job status to COMPLETED (ready for clipping) or FAILED

    print(f"[VIDEO_PROCESSOR] Started background task for Job ID: {job_id}")
    print(f"[VIDEO_PROCESSOR] Source URL: {source_url}, Source Filepath: {source_filepath}")

    job = db_session.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
    if job:
        job.status = "IN_PROGRESS"
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)

    # For now, immediately mark as completed for demonstration
    if job:
        job.status = "COMPLETED"
        job.processing_log = "Simulated successful video download."
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        print(f"[VIDEO_PROCESSOR] Job {job_id} simulated completion (ready for clipping).")


@app.post("/video-processing/submit", response_model=VideoProcessingJob)
async def submit_video_for_processing(
    background_tasks: BackgroundTasks,
    source_url: Optional[str] = None,
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    if not source_url and not file:
        raise HTTPException(status_code=400, detail="Either source_url or a file must be provided.")
    if source_url and file:
        raise HTTPException(status_code=400, detail="Cannot provide both source_url and a file.")

    source_filepath = None
    if file:
        # In a real scenario, upload file to temporary storage (e.g., S3)
        # For this demo, just note the filename
        source_filepath = os.path.join("temp_uploads", file.filename) # Conceptual path
        print(f"[VIDEO_PROCESSING] File uploaded conceptually: {source_filepath}")

    # Create initial job entry
    job = VideoProcessingJobModel(
        source_url=source_url,
        source_filepath=source_filepath,
        status="PENDING",
        date_submitted=datetime.utcnow()
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Add the processing task to background
    # Pass a new session to the background task to avoid session conflicts
    background_tasks.add_task(process_video_background_task, job.id, job.source_url, job.source_filepath, SessionLocal())

    return job

@app.get("/video-processing/{job_id}/status", response_model=VideoProcessingJob)
def get_video_processing_status(job_id: int, db: Session = Depends(get_db)):
    job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Video processing job not found.")
    return job

@app.get("/video-processing/{job_id}/segments", response_model=List[VideoSegment])
def get_video_segments_for_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Video processing job not found.")
    return job.segments

@app.post("/video-processing/clip", response_model=VideoSegment)
async def clip_video_segment(
    job_id: int = Body(...),
    start_time: float = Body(...),
    end_time: float = Body(...),
    drill_id: int = Body(...),
    output_type: str = Body("both"), # 'video', 'audio', or 'both'
    db: Session = Depends(get_db)
):
    job = db.query(VideoProcessingJobModel).filter(VideoProcessingJobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Video processing job not found.")

    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found.")

    if output_type not in ["video", "audio", "both"]:
        raise HTTPException(status_code=400, detail="Invalid output_type. Must be 'video', 'audio', or 'both'.")

    # Create segment entry in DB
    segment = VideoSegmentModel(
        job_id=job.id,
        segment_start_time=start_time,
        segment_end_time=end_time
    )
    db.add(segment)
    db.commit()
    db.refresh(segment)

    # In a real scenario, this would trigger an external worker
    # that uses FFmpeg to clip the video and/or extract audio.
    # The worker would then update the segment and drill with the new URLs.

    # Simulate the clipping and update for now
    print(f"[CLIPPER] Simulating clipping for segment {segment.id} and updating drill {drill.id}")

    # Placeholder URLs
    clipped_video_url = f"https://res.cloudinary.com/demo/video/upload/sample_clipped_{segment.id}.mp4"
    extracted_audio_url = f"https://res.cloudinary.com/demo/video/upload/sample_audio_{segment.id}.mp3"

    segment.video_url = clipped_video_url if output_type in ["video", "both"] else None
    segment.audio_url = extracted_audio_url if output_type in ["audio", "both"] else None

    if output_type in ["video", "both"]:
        drill.video_url = clipped_video_url
    if output_type in ["audio", "both"]:
        drill.audio_url = extracted_audio_url

    db.add(segment)
    db.add(drill)
    db.commit()
    db.refresh(segment)

    return segment


from video_utils import get_video_metadata, get_video_segments, process_and_upload_segment, remote_process_and_upload_segment, get_yt_dlp_cookie_file

# ===================== NEW VIDEO ANALYSIS ENDPOINTS =====================

async def process_video_analysis_task(job_id: int, video_path: str, tmp_dir: str):
    """
    Background task to extract audio, upload to Cloudinary, call ASR Space, and update job.
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
        
        asr_endpoint = asr_space_url.rstrip("/") + "/transcribe"
        print(f"[WORKER] Proxying video file for Job {job_id} to ASR Space...")
        
        hf_token = os.getenv("HUGGINGFACE_API_KEY")
        headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
        
        with open(video_path, "rb") as f:
            resp = requests.post(
                asr_endpoint, 
                files={"audio_file": (os.path.basename(video_path), f, "video/mp4")},
                headers=headers,
                timeout=600
            )
        
        resp.raise_for_status()
        asr_data = resp.json()
        
        segments = asr_data.get("segments", [])
        
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
        # Create temp directory
        tmp_dir = tempfile.mkdtemp()
        video_path = os.path.join(tmp_dir, video.filename)
        
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
            # Cleanup temp directory after immediate processing
            try:
                if os.path.exists(tmp_dir):
                    shutil.rmtree(tmp_dir)
                    print(f"[API] Cleaned up temp directory after immediate processing: {tmp_dir}")
            except Exception as e:
                print(f"[API] Error cleaning temp directory: {e}")
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
            
    return {
        "id": job.id,
        "status": job.status,
        "error_message": job.error_message,
        "segments": segments
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

@app.post("/video-analysis/translate")
async def translate_video_segments(
    segments: List[Dict] = Body(...),
    source_lang: str = Body("auto")
):
    """
    Translate a list of video segments to Catalan.
    """
    try:
        translator = GoogleTranslator(source=source_lang, target='ca')
        
        translated_segments = []
        for seg in segments:
            original_text = seg.get("text", "")
            if original_text:
                try:
                    catalan_text = translator.translate(original_text)
                    seg["text_catalan"] = catalan_text
                except Exception as e:
                    print(f"[API] Translation error for segment: {e}")
                    seg["text_catalan"] = ""
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
                # Smart mapping: Only put in Tachelhit if it's Berber (shi) or if we don't know
                drill_tachelhit = original_text if source_lang in [None, 'shi', 'ber'] else None
                drill_arabic = original_text if source_lang == 'ar' else None

                db_drill = DrillModel(
                    text_catalan=seg.get("text_catalan"),
                    text_tachelhit=drill_tachelhit,
                    text_arabic=drill_arabic,
                    tag=tag or "file_import",
                    author="Manual Upload"
                )
                db.add(db_drill)
                db.commit()
                db.refresh(db_drill)
                
                try:
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
                # Smart mapping
                drill_tachelhit = original_text if source_lang in [None, 'shi', 'ber'] else None
                drill_arabic = original_text if source_lang == 'ar' else None

                db_drill = DrillModel(
                    text_catalan=seg.get("text_catalan"),
                    text_tachelhit=drill_tachelhit,
                    text_arabic=drill_arabic,
                    tag=tag or "video_capture"
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
        "database_url": DATABASE_URL,
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
        added = 0
        for sample in samples:
            # Check if a drill with same text exists (optional)
            existing = db.query(DrillModel).filter(
                DrillModel.text_catalan == sample.text_catalan
            ).first()
            if not existing:
                db.add(sample)
                added += 1
        db.commit()
        # Refresh IDs
        for sample in samples:
            if sample.id is None:
                db.refresh(sample)
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
        added = 0
        for sample in samples:
            existing = db.query(DrillModel).filter(
                DrillModel.text_catalan == sample.text_catalan
            ).first()
            if not existing:
                db.add(sample)
                added += 1
        db.commit()
        for sample in samples:
            if sample.id is None:
                db.refresh(sample)
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
        
        # Since this space only returns the transcription string, we set rough and corrected to the same
        corrected = rough
        score = 1.0

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
            trimmed = audio.subclip(start_time, min(end_time, audio.duration))
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

        # Cleanup
        os.unlink(tmp_in_path)
        os.unlink(tmp_out_path)

        return {"url": url}

    except Exception as e:
        print(f"[TRIM] Error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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
                    video_url=youtube_url
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
                    drill_ids=",".join(str(did) for did in drill_ids)
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

if __name__ == "__main__":
    import uvicorn
    print("=" * 80)
    print("Starting Tachelhit Drills backend server")
    print(f"Listening on http://0.0.0.0:8000")
    print("=" * 80)
    # Nota: No se ha desplegado a Render automáticamente; se necesita push a GitHub.
    uvicorn.run(app, host="0.0.0.0", port=8000)
