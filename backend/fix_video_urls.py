import os
import sqlite3
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from datetime import datetime

load_dotenv("backend/.env")

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def fix_video_urls():
    db_path = "backend/drills.db"
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # We'll use a sample video from Cloudinary or upload a new one if needed
        # For now, let's see if we can find any valid Cloudinary URL in the DB to reuse or use a placeholder
        
        # Upload a real (small) video to Cloudinary to get a valid URL
        print("Uploading a test video to Cloudinary...")
        # A tiny valid MP4 file (base64) - this is just a placeholder, in reality we'd need a real file
        # Using a public sample for now to ensure it works
        test_video_url = "https://res.cloudinary.com/demo/video/upload/dog.mp4"
        
        result = cloudinary.uploader.upload(
            test_video_url,
            folder="tachelhit/test",
            resource_type="video"
        )
        new_url = result['secure_url']
        print(f"✅ New Cloudinary Video URL: {new_url}")

        # Update the drills that have YouTube URLs to use this Cloudinary URL instead
        cursor.execute("UPDATE drills SET video_url = ? WHERE video_url LIKE '%youtube.com%' OR video_url IS NULL", (new_url,))
        print(f"✅ Updated {cursor.rowcount} drills.")
        
        conn.commit()
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix_video_urls()
