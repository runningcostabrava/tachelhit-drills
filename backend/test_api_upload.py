import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_api_upload():
    print("Testing API Upload...")
    API_URL = "http://localhost:8000/upload-media/1/video"
    
    # Check if backend is running (optional, but good for local)
    try:
        requests.get("http://localhost:8000/health", timeout=2)
    except:
        print("❌ Backend not running on localhost:8000. Please start it first.")
        return

    # Create a dummy video file
    dummy_file_path = "test_video.mp4"
    with open(dummy_file_path, "wb") as f:
        f.write(b"dummy video content")

    try:
        with open(dummy_file_path, "rb") as f:
            files = {"file": ("test_video.mp4", f, "video/mp4")}
            print(f"Sending POST request to {API_URL}...")
            response = requests.post(API_URL, files=files)
            
        if response.status_code == 200:
            print(f"✅ API Upload successful! Response: {response.json()}")
        else:
            print(f"❌ API Upload failed with status {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Error during API upload: {e}")
    finally:
        if os.path.exists(dummy_file_path):
            os.remove(dummy_file_path)

if __name__ == "__main__":
    test_api_upload()
