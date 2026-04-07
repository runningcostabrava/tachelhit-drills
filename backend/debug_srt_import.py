#!/usr/bin/env python3
"""
Debug script to test SRT import logic directly without HTTP server.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Drill as DrillModel
from srt_parser import parse_srt_content, create_youtube_url_with_timestamp
from deep_translator import GoogleTranslator

# Create database connection
DATABASE_URL = "sqlite:///drills.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

# Test SRT content
test_srt = '''1
00:00:01,000 --> 00:00:03,000
Hola, com estàs?

2
00:00:05,000 --> 00:00:07,000
Estic bé, gràcies.

3
00:00:10,000 --> 00:00:12,000
Què fas avui?'''

# Parse SRT
segments = parse_srt_content(test_srt)
print(f"Parsed {len(segments)} segments")

# Create translators
translator_ca_to_ar = GoogleTranslator(source='ca', target='ar')

# Create session
db = SessionLocal()

drill_ids = []
created_drills = []

# Create a drill for each segment
for i, segment in enumerate(segments):
    try:
        print(f"\n--- Processing segment {i+1} ---")
        print(f"Text: {segment['text']}")
        print(f"Start time: {segment['start_time']}")
        
        # Create YouTube URL with timestamp
        youtube_url = "https://www.youtube.com/watch?v=test123"
        youtube_url_with_time = create_youtube_url_with_timestamp(youtube_url, segment["start_time"])
        print(f"YouTube URL: {youtube_url_with_time}")
        
        # Create drill with the segment text as Catalan text
        db_drill = DrillModel(
            text_catalan=segment["text"],
            tag="youtube_srt_test",
            author="test_user",
            video_url=youtube_url_with_time
        )
        
        print(f"Created DrillModel: text_catalan={db_drill.text_catalan[:50]}...")
        
        db.add(db_drill)
        db.flush()  # Get the ID without committing
        print(f"Drill ID: {db_drill.id}")
        
        # Generate Arabic translation
        try:
            arabic_text = translator_ca_to_ar.translate(segment["text"])
            db_drill.text_arabic = arabic_text
            print(f"Arabic translation: {arabic_text}")
        except Exception as trans_e:
            print(f"Translation error: {trans_e}")
        
        # Note: Skipping TTS for now to simplify
        
        drill_ids.append(db_drill.id)
        created_drills.append(db_drill)
        
        print(f"Successfully created drill {db_drill.id} for segment {i+1}")
        
    except Exception as segment_e:
        print(f"ERROR creating drill for segment {i+1}: {segment_e}")
        import traceback
        traceback.print_exc()
        continue

# Commit all drills
try:
    db.commit()
    print(f"\nCommitted {len(drill_ids)} drills to database")
except Exception as commit_e:
    print(f"ERROR committing: {commit_e}")
    import traceback
    traceback.print_exc()
    db.rollback()

# Verify drills were created
print(f"\n--- Verification ---")
all_drills = db.query(DrillModel).filter(DrillModel.tag == "youtube_srt_test").all()
print(f"Found {len(all_drills)} drills with tag 'youtube_srt_test' in database")
for drill in all_drills:
    print(f"  Drill {drill.id}: {drill.text_catalan[:50]}...")

db.close()