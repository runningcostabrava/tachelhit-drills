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

from backend.models import Base, Drill as DrillModel

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
            
            # --- Clean image_url ---
            if drill.image_url:
                if drill.image_url.startswith("https//"):
                    drill.image_url = drill.image_url.replace("https//", "https://")
                elif drill.image_url.startswith("http//"):
                    drill.image_url = drill.image_url.replace("http//", "http://")
                
                # Check for API_BASE prefix and remove it if it precedes a valid Cloudinary URL
                if "tachelhit-drills-api.onrender.com" in drill.image_url and "res.cloudinary.com" in drill.image_url:
                    drill.image_url = drill.image_url.split("tachelhit-drills-api.onrender.com", 1)[-1]
                    if drill.image_url.startswith("https//"): # Re-check after stripping prefix
                        drill.image_url = drill.image_url.replace("https//", "https://")
            
            # --- Clean audio_url ---
            if drill.audio_url:
                if drill.audio_url.startswith("https//"):
                    drill.audio_url = drill.audio_url.replace("https//", "https://")
                elif drill.audio_url.startswith("http//"):
                    drill.audio_url = drill.audio_url.replace("http//", "http://")
                
                if "tachelhit-drills-api.onrender.com" in drill.audio_url and "res.cloudinary.com" in drill.audio_url:
                    drill.audio_url = drill.audio_url.split("tachelhit-drills-api.onrender.com", 1)[-1]
                    if drill.audio_url.startswith("https//"):
                        drill.audio_url = drill.audio_url.replace("https//", "https://")
            
            # --- Clean video_url ---
            if drill.video_url:
                if drill.video_url.startswith("https//"):
                    drill.video_url = drill.video_url.replace("https//", "https://")
                elif drill.video_url.startswith("http//"):
                    drill.video_url = drill.video_url.replace("http//", "http://")
                
                if "tachelhit-drills-api.onrender.com" in drill.video_url and "res.cloudinary.com" in drill.video_url:
                    drill.video_url = drill.video_url.split("tachelhit-drills-api.onrender.com", 1)[-1]
                    if drill.video_url.startswith("https//"):
                        drill.video_url = drill.video_url.replace("https//", "https://")

            if (original_image_url != drill.image_url or 
                original_audio_url != drill.audio_url or 
                original_video_url != drill.video_url):
                print(f"Drill {drill.id}: Cleaned URLs")
                print(f"  Image: '{original_image_url}' -> '{drill.image_url}'")
                print(f"  Audio: '{original_audio_url}' -> '{drill.audio_url}'")
                print(f"  Video: '{original_video_url}' -> '{drill.video_url}'")
                cleaned_count += 1
                db.add(drill) # Mark as modified

        if cleaned_count > 0:
            db.commit()
            print(f"\nSuccessfully cleaned {cleaned_count} drill media URLs.")
        else:
            print("\nNo malformed media URLs found in drills.")

    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting media URL cleanup script...")
    clean_media_urls()
    print("Cleanup script finished.")
