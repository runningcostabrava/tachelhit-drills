import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Database setup (copy-pasted from main.py) ---
import sys
import os

# Add the parent directory to sys.path to allow absolute imports from the project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.models import Base, Drill as DrillModel, Test as TestModel, YouTubeShort as YouTubeShortModel
from backend.schemas import normalize_media_url

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///drills.db")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine) # Ensure tables are created if not already

# --- Cleanup Script Logic ---
def clean_media_urls():
    db = SessionLocal()
    try:
        drills = db.query(DrillModel).all()
        cleaned_count = 0

        for drill in drills:
            original_image_url = drill.image_url
            original_audio_url = drill.audio_url
            original_video_url = drill.video_url
            
            # Normalize each URL using the shared function
            if drill.image_url:
                drill.image_url = normalize_media_url(drill.image_url)
            if drill.audio_url:
                drill.audio_url = normalize_media_url(drill.audio_url)
            if drill.video_url:
                drill.video_url = normalize_media_url(drill.video_url)

            if (original_image_url != drill.image_url or 
                original_audio_url != drill.audio_url or 
                original_video_url != drill.video_url):
                print(f"Drill {drill.id}: Cleaned URLs")
                print(f"  Image: '{original_image_url}' -> '{drill.image_url}'")
                print(f"  Audio: '{original_audio_url}' -> '{drill.audio_url}'")
                print(f"  Video: '{original_video_url}' -> '{drill.video_url}'")
                cleaned_count += 1
                db.add(drill) # Mark as modified

        # Clean Test.video_url
        tests = db.query(TestModel).all()
        for test in tests:
            original_video_url = test.video_url
            if test.video_url:
                test.video_url = normalize_media_url(test.video_url)
            if original_video_url != test.video_url:
                print(f"Test {test.id}: Cleaned video_url")
                print(f"  From: '{original_video_url}'")
                print(f"  To:   '{test.video_url}'")
                cleaned_count += 1
                db.add(test)

        # Clean YouTubeShort.video_path
        shorts = db.query(YouTubeShortModel).all()
        for short in shorts:
            original_video_path = short.video_path
            if short.video_path:
                short.video_path = normalize_media_url(short.video_path)
            if original_video_path != short.video_path:
                print(f"YouTubeShort {short.id}: Cleaned video_path")
                print(f"  From: '{original_video_path}'")
                print(f"  To:   '{short.video_path}'")
                cleaned_count += 1
                db.add(short)

        if cleaned_count > 0:
            db.commit()
            print(f"\nSuccessfully cleaned {cleaned_count} media URLs across all tables.")
        else:
            print("\nNo malformed media URLs found in any table.")

    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting media URL cleanup script...")
    clean_media_urls()
    print("Cleanup script finished.")
