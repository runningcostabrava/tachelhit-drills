"""
Export all drills, tests, and test attempts to JSON
"""
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Drill, Test, TestAttempt
from datetime import datetime

# Create engine
engine = create_engine('sqlite:///drills.db')
Session = sessionmaker(bind=engine)
db = Session()

def export_data():
    # Export drills
    drills = db.query(Drill).all()
    drills_data = []
    for drill in drills:
        drills_data.append({
            'id': drill.id,
            'text_catalan': drill.text_catalan,
            'text_tachelhit': drill.text_tachelhit,
            'text_arabic': drill.text_arabic,
            'audio_url': drill.audio_url,
            'video_url': drill.video_url,
            'image_url': drill.image_url,
            'date_created': drill.date_created.isoformat() if drill.date_created else None,
        })

    # Export tests
    tests = db.query(Test).all()
    tests_data = []
    for test in tests:
        tests_data.append({
            'id': test.id,
            'title': test.title,
            'description': test.description,
            'question_type': test.question_type,
            'hint_level': test.hint_level,
            'hint_percentage': test.hint_percentage,
            'hint_tries_before_reveal': test.hint_tries_before_reveal,
            'time_limit_seconds': test.time_limit_seconds,
            'passing_score': test.passing_score,
            'drill_ids': test.drill_ids,
            'date_created': test.date_created.isoformat() if test.date_created else None,
        })

    # Export test attempts
    attempts = db.query(TestAttempt).all()
    attempts_data = []
    for attempt in attempts:
        attempts_data.append({
            'id': attempt.id,
            'test_id': attempt.test_id,
            'score': attempt.score,
            'time_taken_seconds': attempt.time_taken_seconds,
            'date_taken': attempt.date_taken.isoformat() if attempt.date_taken else None,
        })

    # Combine all data
    export = {
        'export_date': datetime.now().isoformat(),
        'drills': drills_data,
        'tests': tests_data,
        'test_attempts': attempts_data,
    }

    # Write to file
    with open('data_export.json', 'w', encoding='utf-8') as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    print(f"Exported {len(drills_data)} drills")
    print(f"Exported {len(tests_data)} tests")
    print(f"Exported {len(attempts_data)} test attempts")
    print(f"Data saved to: data_export.json")

if __name__ == '__main__':
    export_data()
    db.close()
