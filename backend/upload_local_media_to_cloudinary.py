"""
Upload all local media files to production (which will store them in Cloudinary)
"""
import os
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Drill
from dotenv import load_dotenv

load_dotenv()

# Local database
LOCAL_DB = "sqlite:///drills.db"
engine = create_engine(LOCAL_DB, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

# Production API
PRODUCTION_API = "https://tachelhit-drills-api.onrender.com"

def upload_file_to_production(drill_id, media_type, file_path):
    """Upload a single file to production API"""
    if not os.path.exists(file_path):
        print(f"  [X] File not found: {file_path}")
        return False

    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            url = f"{PRODUCTION_API}/upload-media/{drill_id}/{media_type}"

            print(f"  [^] Uploading {media_type}: {os.path.basename(file_path)} ({os.path.getsize(file_path) / 1024:.1f} KB)")

            response = requests.post(url, files=files, timeout=60)

            if response.status_code == 200:
                result = response.json()
                cloudinary_url = result.get('url', 'Unknown')
                print(f"  [OK] Uploaded to Cloudinary: {cloudinary_url}")
                return True
            else:
                print(f"  [X] Upload failed: {response.status_code} - {response.text}")
                return False

    except Exception as e:
        print(f"  [X] Error uploading: {str(e)}")
        return False

def main():
    print("=" * 80)
    print("UPLOADING LOCAL MEDIA TO PRODUCTION (CLOUDINARY)")
    print("=" * 80)
    print(f"Local DB: {LOCAL_DB}")
    print(f"Production API: {PRODUCTION_API}")
    print("=" * 80)

    db = SessionLocal()
    drills = db.query(Drill).all()

    stats = {
        'audio': {'total': 0, 'success': 0, 'failed': 0},
        'video': {'total': 0, 'success': 0, 'failed': 0},
        'image': {'total': 0, 'success': 0, 'failed': 0}
    }

    print(f"\nFound {len(drills)} drills in local database\n")

    for drill in drills:
        print(f"Drill #{drill.id}: {drill.text_catalan or '(no text)'}")

        # Upload audio
        if drill.audio_url and drill.audio_url.startswith('/media/audio/'):
            stats['audio']['total'] += 1
            file_path = os.path.join('media', drill.audio_url.replace('/media/', ''))
            if upload_file_to_production(drill.id, 'audio', file_path):
                stats['audio']['success'] += 1
            else:
                stats['audio']['failed'] += 1

        # Upload video
        if drill.video_url and drill.video_url.startswith('/media/video/'):
            stats['video']['total'] += 1
            file_path = os.path.join('media', drill.video_url.replace('/media/', ''))
            if upload_file_to_production(drill.id, 'video', file_path):
                stats['video']['success'] += 1
            else:
                stats['video']['failed'] += 1

        # Upload image
        if drill.image_url and drill.image_url.startswith('/media/images/'):
            stats['image']['total'] += 1
            file_path = os.path.join('media', drill.image_url.replace('/media/', ''))
            if upload_file_to_production(drill.id, 'image', file_path):
                stats['image']['success'] += 1
            else:
                stats['image']['failed'] += 1

        print()  # Blank line between drills

    db.close()

    # Summary
    print("=" * 80)
    print("UPLOAD SUMMARY")
    print("=" * 80)
    print(f"Audio:  {stats['audio']['success']}/{stats['audio']['total']} uploaded successfully, {stats['audio']['failed']} failed")
    print(f"Video:  {stats['video']['success']}/{stats['video']['total']} uploaded successfully, {stats['video']['failed']} failed")
    print(f"Images: {stats['image']['success']}/{stats['image']['total']} uploaded successfully, {stats['image']['failed']} failed")
    print("=" * 80)

    total_success = stats['audio']['success'] + stats['video']['success'] + stats['image']['success']
    total_failed = stats['audio']['failed'] + stats['video']['failed'] + stats['image']['failed']

    if total_failed == 0:
        print(f"[SUCCESS] All {total_success} files uploaded successfully to Cloudinary!")
    else:
        print(f"[WARNING] {total_success} succeeded, {total_failed} failed")

    print("\nAll uploaded files are now stored in Cloudinary and will persist!")
    print("=" * 80)

if __name__ == "__main__":
    main()
