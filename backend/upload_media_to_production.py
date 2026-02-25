"""
Upload all local media files (audio and images) to production server
"""
import os
import requests
from pathlib import Path

API_URL = "https://tachelhit-drills-api.onrender.com"
MEDIA_ROOT = "media"

def upload_media_file(drill_id, media_type, file_path):
    """Upload a single media file to production"""
    endpoint = f"{API_URL}/upload-media/{drill_id}/{media_type}"

    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f)}
        try:
            response = requests.post(endpoint, files=files, timeout=60)
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"Error {response.status_code}: {response.text}"
        except Exception as e:
            return False, str(e)

def extract_drill_id(filename):
    """Extract drill ID from filename like 'audio_12_1770639087.webm'"""
    try:
        parts = filename.split('_')
        if len(parts) >= 2:
            return int(parts[1])
    except:
        pass
    return None

def upload_all_media():
    stats = {
        'audio': {'success': 0, 'failed': 0},
        'image': {'success': 0, 'failed': 0}
    }

    # Upload audio files
    audio_dir = Path(MEDIA_ROOT) / 'audio'
    if audio_dir.exists():
        audio_files = list(audio_dir.glob('*.webm'))
        print(f"\nUploading {len(audio_files)} audio files...")

        for audio_file in audio_files:
            drill_id = extract_drill_id(audio_file.name)
            if drill_id:
                print(f"  Uploading {audio_file.name} for drill {drill_id}...", end=' ')
                success, result = upload_media_file(drill_id, 'audio', audio_file)
                if success:
                    print("OK")
                    stats['audio']['success'] += 1
                else:
                    print(f"FAILED: {result}")
                    stats['audio']['failed'] += 1
            else:
                print(f"  Skipping {audio_file.name} (can't extract drill ID)")

    # Upload image files
    image_dir = Path(MEDIA_ROOT) / 'images'
    if image_dir.exists():
        image_files = list(image_dir.glob('*.jpg'))
        print(f"\nUploading {len(image_files)} image files...")

        for image_file in image_files:
            drill_id = extract_drill_id(image_file.name)
            if drill_id:
                print(f"  Uploading {image_file.name} for drill {drill_id}...", end=' ')
                success, result = upload_media_file(drill_id, 'image', image_file)
                if success:
                    print("OK")
                    stats['image']['success'] += 1
                else:
                    print(f"FAILED: {result}")
                    stats['image']['failed'] += 1
            else:
                print(f"  Skipping {image_file.name} (can't extract drill ID)")

    # Print summary
    print("\n" + "="*60)
    print("UPLOAD SUMMARY")
    print("="*60)
    print(f"Audio files - Success: {stats['audio']['success']}, Failed: {stats['audio']['failed']}")
    print(f"Image files - Success: {stats['image']['success']}, Failed: {stats['image']['failed']}")
    print("="*60)

if __name__ == '__main__':
    print("Starting media upload to production...")
    print(f"Target: {API_URL}")
    upload_all_media()
