import requests
import json

# Test SRT import endpoint
url = "http://localhost:8000/srt/import"

# Test SRT content with clean Catalan text
test_srt = '''1
00:00:01,000 --> 00:00:03,000
Hola, com estàs?

2
00:00:05,000 --> 00:00:07,000
Estic bé, gràcies.

3
00:00:10,000 --> 00:00:12,000
Què fas avui?'''

# Test YouTube video URL (example)
youtube_url = "https://www.youtube.com/watch?v=test123"

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

print("Testing SRT import endpoint with clean text...")
print(f"URL: {url}")
print(f"SRT segments: 3")
print(f"YouTube URL: {youtube_url}")

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"\nResponse status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Full response: {json.dumps(result, indent=2)}")
        print(f"Success! Created {result.get('drill_count', 0)} drills")
        print(f"Drill IDs: {result.get('drill_ids', [])}")
        if result.get('test_id'):
            print(f"Test created with ID: {result.get('test_id')}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Exception: {e}")