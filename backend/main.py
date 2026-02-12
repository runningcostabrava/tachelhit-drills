import os
import json
from datetime import datetime
from urllib.parse import quote
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Body, BackgroundTasks
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import requests
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

from deep_translator import GoogleTranslator

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

from models import Base, Drill as DrillModel, Test as TestModel, TestAttempt as TestAttemptModel, YouTubeShort as YouTubeShortModel, VideoProcessingJob as VideoProcessingJobModel, VideoSegment as VideoSegmentModel  # ← Alias for ORM models
from schemas import DrillCreate, DrillUpdate, Drill, TestCreate, TestUpdate, Test, TestAttemptCreate, TestAttempt, YouTubeShortCreate, YouTubeShort, VideoProcessingJobCreate, VideoProcessingJob, VideoSegmentCreate, VideoSegment  # ← Pydantic schemas
from shorts_generator import generate_youtube_short

# Translators
translator_ca_to_ar = GoogleTranslator(source='ca', target='ar')
translator_ca_to_en = GoogleTranslator(source='ca', target='en')

# Config
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "dX9JkRJYfaRQUZdi6tKsF1TfJT44HnZMAPu2RyA4vt0JyRbzmdiVYGgW")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///drills.db")
# Usar el nuevo Space tachelhit-video-generator
HUGGINGFACE_SPACE_URL = os.getenv("HUGGINGFACE_SPACE_URL", "https://josepabloucr-tachelhit-video-generator.hf.space")

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
        import tempfile
        import shutil

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

# Optionally check and fix schema before creating tables
# Set CHECK_SCHEMA environment variable to "1" to enable
if os.getenv("CHECK_SCHEMA") == "1":
    print("[SCHEMA] Checking and fixing schema...")
    try:
        from check_and_fix_schema import check_and_fix
        check_and_fix()
        print("[SCHEMA] Schema check complete.")
    except Exception as e:
        print(f"[SCHEMA] ERROR during schema check: {e}")
        import traceback
        traceback.print_exc()
        # Continue anyway; don't crash the app

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tachelhit Drills API")

# CORS configuration - allow frontend URL
allowed_origins_base = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://localhost:5176",
    "http://localhost:4173", # Vite default preview server port
    "http://localhost:3000",
    "https://tachelhit-drills.vercel.app",  # Production URL (without trailing slash)
    "https://tachelhit-drills.vercel.app/", # Production URL (with trailing slash)
]

# Remove duplicates and None values
# FRONTEND_URL environment variable is no longer explicitly added to this list for CORS
allowed_origins = list(set(filter(None, allowed_origins_base)))

print("=" * 80)
print("CORS CONFIGURATION")
print("=" * 80)
print(f"FRONTEND_URL from env: {FRONTEND_URL}")
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

@app.get("/health")
def health_check():
    print(f"[HEALTH] Health check requested at {datetime.utcnow().isoformat()}")
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "frontend_url": FRONTEND_URL,
        "api_base": "https://tachelhit-drills-api.onrender.com",
        "cors_allowed": allowed_origins,
        "service": "tachelhit-drills-backend"
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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===================== CRUD =====================
@app.get("/drills/", response_model=list[Drill])
def get_drills(db: Session = Depends(get_db)):
    return db.query(DrillModel).order_by(DrillModel.date_created.desc()).all()

@app.post("/drills/", response_model=Drill)
def create_drill(db: Session = Depends(get_db)): # Removed `drill: DrillCreate` as we're creating an empty one
    try:
        # Create a new DrillModel instance without any arguments
        # This lets the database handle default values, including the auto-incrementing ID
        db_drill = DrillModel()

        # Any default text processing can go here if needed, but not based on input

        db.add(db_drill)
        db.commit()
        db.refresh(db_drill)
        return db_drill
    except Exception as e:
        db.rollback() # Rollback in case of error
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

# ===================== Image Generation =====================
@app.post("/generate-image/{drill_id}")
def generate_image(drill_id: int, body: dict = Body(None), db: Session = Depends(get_db)):
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill or not drill.text_catalan:
        raise HTTPException(status_code=400, detail="Drill or Catalan text not found")

    try:
        print(f"[IMAGE] Searching image for drill {drill_id}: {drill.text_catalan}")

        # Check if custom search query was provided
        if body and body.get('search_query'):
            user_query = body['search_query']
            print(f"[IMAGE] Using custom search phrase: {user_query}")

            # Translate custom query to English if it's not already in English
            try:
                translated = translator_ca_to_en.translate(user_query)
                print(f"[IMAGE] Translated custom phrase: {user_query} -> {translated}")
                # Enhance the translated query
                search_query = enhance_search_query(translated)
                print(f"[IMAGE] Enhanced query: {translated} -> {search_query}")
            except Exception as trans_error:
                print(f"[IMAGE] Translation failed: {trans_error}, using as-is")
                search_query = enhance_search_query(user_query)
        else:
            # Auto-translate Catalan to English for better Pexels search results
            try:
                translated = translator_ca_to_en.translate(drill.text_catalan)
                print(f"[IMAGE] Auto-translated to English: {drill.text_catalan} -> {translated}")
                # Enhance the translated query for better conceptual results
                search_query = enhance_search_query(translated)
                print(f"[IMAGE] Enhanced query: {translated} -> {search_query}")
            except Exception as trans_error:
                print(f"[IMAGE] Translation failed: {trans_error}, using original text")
                search_query = enhance_search_query(drill.text_catalan)
        api_url = "https://api.pexels.com/v1/search"
        headers = {
            "Authorization": PEXELS_API_KEY
        }
        params = {
            "query": search_query,
            "per_page": 1,
            "orientation": "landscape"
        }

        print(f"[IMAGE] Searching Pexels for: {search_query}")
        print(f"[IMAGE] API URL: {api_url}")

        # Search for photos
        search_response = requests.get(api_url, headers=headers, params=params, timeout=10)
        print(f"[IMAGE] Search response status: {search_response.status_code}")
        search_response.raise_for_status()

        search_data = search_response.json()
        print(f"[IMAGE] Found {search_data.get('total_results', 0)} results")

        if not search_data.get('photos') or len(search_data['photos']) == 0:
            raise HTTPException(status_code=404, detail=f"No images found for '{search_query}'")

        # Get the first photo
        photo = search_data['photos'][0]
        photo_url = photo['src']['large']  # or 'medium', 'original'
        photographer = photo.get('photographer', 'Unknown')

        print(f"[IMAGE] Found photo by {photographer}")
        print(f"[IMAGE] Downloading from: {photo_url}")

        # Download the image
        image_response = requests.get(photo_url, timeout=30)
        image_response.raise_for_status()
        print(f"[IMAGE] Image downloaded: {len(image_response.content)} bytes")

        # Check if Cloudinary is configured
        use_cloudinary = bool(os.getenv("CLOUDINARY_CLOUD_NAME"))

        if use_cloudinary:
            # Upload to Cloudinary
            print(f"[IMAGE] Uploading to Cloudinary")
            result = cloudinary.uploader.upload(
                image_response.content,
                folder="tachelhit/images",
                public_id=f"img_{drill_id}_{int(datetime.utcnow().timestamp())}",
                resource_type="image"
            )
            drill.image_url = result['secure_url']
            print(f"[IMAGE] Cloudinary URL: {drill.image_url}")
        else:
            # Save locally
            filename = f"img_{drill_id}_{int(datetime.now().timestamp())}.jpg"
            filepath = os.path.join(MEDIA_ROOT, "images", filename)
            print(f"[IMAGE] Saving locally to: {filepath}")

            with open(filepath, "wb") as f:
                f.write(image_response.content)

            drill.image_url = f"/media/images/{filename}"
            print(f"[IMAGE] Image saved locally: {drill.image_url}")

        db.commit()
        print(f"[IMAGE] Drill updated with image URL")
        print(f"[IMAGE] Photo by {photographer} from Pexels")

        return {"image_url": drill.image_url, "photographer": photographer}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[IMAGE] ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ===================== Media Upload =====================
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
    average_score = sum(a.score for a in attempts) / total_attempts
    passed_attempts = sum(1 for a in attempts if a.score >= test.passing_score)
    completion_rate = (passed_attempts / total_attempts) * 100
    average_time = sum(a.time_taken_seconds for a in attempts) / total_attempts

    return {
        "total_attempts": total_attempts,
        "average_score": round(average_score, 2),
        "completion_rate": round(completion_rate, 2),
        "average_time": round(average_time, 2),
        "passed_attempts": passed_attempts
    }

def call_huggingface_space(endpoint: str, payload: dict):
    """
    Calls the Dockerized FastAPI Space.
    Handles the standard JSON response without needing a Gradio client.
    """
    try:
        import requests

        # Ensure we use the exact Space URL
        space_url = "https://josepabloucr-tachelhit-video-generator.hf.space"
        url = f"{space_url}/api/{endpoint}"

        print(f"[HF SPACE] 🚀 Requesting video: {url}")

        # Direct POST request
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()

        result = response.json()

        # Check if the Space returned an internal error
        if result.get("status") == "failed" or "error" in result:
            error_msg = result.get("error", "Unknown Space error")
            print(f"[HF SPACE] ❌ Space Error: {error_msg}")
            raise Exception(error_msg)

        print(f"[HF SPACE] ✅ Video generated: {result.get('video_path')}")
        return result

    except Exception as e:
        print(f"[HF SPACE] 💥 Connection Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Video Generation failed: {str(e)}"
        )
    """
    Debug-enhanced request to Hugging Face Space.
    Prints full URL, payload structure, and raw response details.
    """
    try:
        import requests
        import re
        import json

        space_url = HUGGINGFACE_SPACE_URL

        # 1. URL Correction Logic
        match = re.search(r"huggingface\.co/spaces/([^/]+)/([^/]+)", space_url)
        if match:
            username = match.group(1)
            space_name = match.group(2)
            space_url = f"https://{username}-{space_name}.hf.space"

        # Ensure no double slashes
        base_url = space_url.rstrip("/")

        # !!! CRITICAL DEBUG !!!
        # Check if we are accidentally calling 'predict' when we defined 'generate' in app.py
        target_url = f"{base_url}/api/{endpoint}"

        print("\n" + "="*60)
        print(f"[HF DEBUG] 🚀 Initiating Request")
        print(f"[HF DEBUG] Target URL: {target_url}")
        print(f"[HF DEBUG] Payload Keys: {list(payload.keys())}")
        if "data" in payload:
             # Print first 2 items of data to verify order without dumping huge strings
            print(f"[HF DEBUG] Data Array (First 2 items): {payload['data'][:2]}")
        print("="*60 + "\n")

        response = requests.post(target_url, json=payload, timeout=60)

        print(f"[HF DEBUG] 📡 Response Status: {response.status_code}")

        # Print first 200 chars of response to catch HTML 404 pages or error messages
        response_text = response.text
        print(f"[HF DEBUG] Response Body Preview: {response_text[:200]}...")

        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        print(f"\n[HF DEBUG] ❌ HTTP Error: {e}")
        # If it's a 404, it means the URL is wrong
        if response.status_code == 404:
            print(f"[HF DEBUG] ⚠️  404 NOT FOUND. This means '{target_url}' does not exist.")
            print(f"[HF DEBUG] Check if app.py has api_name='{endpoint}' or @app.post('/api/{endpoint}')")
        raise HTTPException(status_code=500, detail=f"HF Error: {str(e)}")
    except Exception as e:
        print(f"[HF DEBUG] 💥 Unexpected Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")


    """
    Send a request to Hugging Face Space API, automatically correcting the URL format if needed.
    """
    try:
        import requests
        import re

        space_url = HUGGINGFACE_SPACE_URL

        # Check if the URL is in the 'huggingface.co/spaces/' format and convert it
        match = re.search(r"huggingface\.co/spaces/([^/]+)/([^/]+)", space_url)
        if match:
            username = match.group(1)
            space_name = match.group(2)
            correct_url = f"https://{username}-{space_name}.hf.space"
            print(f"[HF SPACE] Corrected URL from {space_url} to {correct_url}")
            space_url = correct_url

        # Gradio exposes endpoints at /api/{endpoint}/
        # Ensure no double slashes
        base_url = space_url.rstrip("/")
        url = f"{base_url}/api/{endpoint}"
        print(f"[HF SPACE] Calling {url} with payload: {payload}")
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[HF SPACE] Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Hugging Face Space request failed: {str(e)}"
        )

# ===================== YOUTUBE SHORTS =====================
@app.post("/generate-short/{drill_id}")
def generate_short(drill_id: int, db: Session = Depends(get_db)):
    drill = db.query(DrillModel).filter(DrillModel.id == drill_id).first()
    if not drill:
        raise HTTPException(status_code=404, detail="Drill not found")

    try:
        print(f"[API] Generating short for drill {drill_id} via Hugging Face Space")

        # Prepare drill data
# Prepare drill data
        drill_data = {
            'text_catalan': drill.text_catalan,
            'text_tachelhit': drill.text_tachelhit,
            'text_arabic': drill.text_arabic,
            'image_url': drill.image_url,
            'audio_url': drill.audio_url,
            'video_url': drill.video_url
        }

        # Generate filename
        filename = f"short_{drill_id}_{int(datetime.now().timestamp())}.mp4"

        # CORRECT PAYLOAD FOR SHORTS
        payload = {
            "data": [
                "short",                    # Type is SHORT
                json.dumps(drill_data),     # Send SINGLE drill data
                None,                       # No list data
                filename,
                0
            ]
        }
        result = call_huggingface_space("predict", payload)

        # Save to database
        short = YouTubeShortModel(
            drill_id=drill_id,
            video_path=result.get('video_path', f"/media/shorts/{filename}"),
            text_catalan=drill.text_catalan,
            text_tachelhit=drill.text_tachelhit,
            text_arabic=drill.text_arabic
        )
        db.add(short)
        db.commit()
        db.refresh(short)

        print(f"[API] Short generated and saved: {short.id}")
        return {"id": short.id, "video_path": short.video_path}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Error generating short: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ===================== DRILL PLAYER DEMO VIDEO =====================
@app.post("/generate-drillplayer-demo/{test_id}")
def generate_drillplayer_demo(test_id: int, db: Session = Depends(get_db)):
    test = db.query(TestModel).filter(TestModel.id == test_id).first()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    try:
        print(f"[API] Generating Drill Player demo for test {test_id} via Hugging Face Space")

        # Get drill IDs from test
        drill_ids = [int(id.strip()) for id in test.drill_ids.split(',') if id.strip()]
        drills = db.query(DrillModel).filter(DrillModel.id.in_(drill_ids)).all()

        if not drills:
            raise HTTPException(status_code=400, detail="Test has no drills")

        # Prepare drill data
# Prepare drill data
        drills_data = []
        for drill in drills:
            drills_data.append({
                'id': drill.id,
                'text_catalan': drill.text_catalan,
                'text_tachelhit': drill.text_tachelhit,
                'text_arabic': drill.text_arabic,
                'image_url': drill.image_url,
                'audio_url': drill.audio_url,
                'audio_tts_url': drill.audio_tts_url,
                'video_url': drill.video_url
            })

        # Generate filename
        filename = f"demo_test_{test_id}_{int(datetime.now().timestamp())}.mp4"

        # CORRECT PAYLOAD FOR DEMO
        payload = {
            "data": [
                "demo",                     # Type is DEMO
                None,                       # No single data
                json.dumps(drills_data),    # Send LIST of drills
                filename,
                test_id
            ]
        }
        result = call_huggingface_space("predict", payload)



        # Return the video path (not saved in database)
        video_path = result.get('video_path', f"/media/shorts/{filename}")
        return {
            "test_id": test_id,
            "video_path": video_path,
            "drill_count": len(drills_data),
            "message": "Demo video generated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[API] Error generating demo video: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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


# ===================== DEBUG ENDPOINTS =====================
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
        return {"error": str(e), "traceback": str(__import__("traceback").format_exc())}

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
