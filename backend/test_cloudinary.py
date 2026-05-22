import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

def test_cloudinary():
    print("Checking Cloudinary configuration...")
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        print("❌ Missing Cloudinary environment variables!")
        return False

    print(f"Cloud Name: {cloud_name}")
    print(f"API Key: {api_key[:5]}...")

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret
    )

    try:
        print("Attempting test upload...")
        # Upload a small dummy file (a 1x1 pixel gif)
        dummy_file = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
        result = cloudinary.uploader.upload(dummy_file, folder="test")
        print(f"✅ Test upload successful! URL: {result['secure_url']}")
        return True
    except Exception as e:
        print(f"❌ Test upload failed: {e}")
        return False

if __name__ == "__main__":
    test_cloudinary()
