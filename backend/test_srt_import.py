import requests
import json

# Test SRT import endpoint
url = "http://localhost:8000/srt/import"

# Test SRT content (Catalan translations from YouTube)
test_srt = '''1
00:02:28,000 --> 00:02:30,000
7aa-+a52t 34-7

2
00:02:30,000 --> 00:02:32,000
7aa#6a52t5a78.3$

3
00:02:36,000 --> 00:02:38,000
3 Hi ha perills per a mi

4
00:02:38,000 --> 00:02:40,000
La situació. El bo s'ha despertat'''

# Test YouTube video URL (example)
youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

payload = {
    "srt_content": test_srt,
    "video_url": youtube_url,
    "tag": "youtube_srt_test",
    "author": "test_user",
    "create_test": False
}

headers = {
    "Content-Type": "application/json"
}

print("Testing SRT import endpoint...")
print(f"URL: {url}")
print(f"SRT segments: 4")
print(f"YouTube URL: {youtube_url}")

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"\nResponse status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Full response: {json.dumps(result, indent=2)}")
        print(f"Success! Created {result.get('drills_created', 0)} drills")
        print(f"Drill IDs: {result.get('drill_ids', [])}")
        if result.get('test_id'):
            print(f"Test created with ID: {result.get('test_id')}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Exception: {e}")