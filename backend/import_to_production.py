"""
Import data to production server
"""
import json
import requests

# Production API URL
API_URL = "https://tachelhit-drills-api.onrender.com"

# Read the exported data
with open('data_export.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Skip test attempts due to schema mismatch
data['test_attempts'] = []

print(f"Loaded data:")
print(f"  - {len(data['drills'])} drills")
print(f"  - {len(data['tests'])} tests")
print(f"  - {len(data['test_attempts'])} test attempts (skipped due to schema)")
print()

# Import to production
print(f"Importing to {API_URL}...")
response = requests.post(f"{API_URL}/import-data/", json=data, timeout=60)

if response.status_code == 200:
    result = response.json()
    print("\nImport successful!")
    print(f"  - Drills imported: {result['imported']['drills']}")
    print(f"  - Tests imported: {result['imported']['tests']}")
    print(f"  - Test attempts imported: {result['imported']['test_attempts']}")
    print(f"  - Skipped (already exist): {result['imported']['skipped']}")
else:
    print(f"\nError: {response.status_code}")
    print(response.text)
