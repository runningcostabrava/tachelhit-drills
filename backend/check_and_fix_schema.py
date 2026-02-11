"""
Script to check and fix missing columns in the database schema.
Run this manually when deploying or after schema changes.
"""
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import ProgrammingError
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///drills.db")

def check_and_fix():
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    # Check if column exists in drills table
    try:
        columns = [col['name'] for col in inspector.get_columns('drills')]
    except Exception as e:
        print(f"Error inspecting table 'drills': {e}")
        # Table might not exist; that's okay, it will be created by ORM
        print("Table 'drills' may not exist yet. Skipping.")
        return
    
    print("Existing columns in drills:", columns)
    
    if 'audio_tts_url' not in columns:
        print("Column 'audio_tts_url' missing. Adding...")
        try:
            with engine.connect() as conn:
                if DATABASE_URL.startswith('sqlite'):
                    # SQLite doesn't support ADD COLUMN IF NOT EXISTS directly
                    # We'll attempt to add and ignore error if already exists
                    try:
                        conn.execute(text("ALTER TABLE drills ADD COLUMN audio_tts_url VARCHAR"))
                    except Exception as e:
                        if 'duplicate column name' in str(e).lower():
                            print("Column already exists (SQLite).")
                        else:
                            raise
                else:
                    # PostgreSQL / other
                    conn.execute(text("ALTER TABLE drills ADD COLUMN IF NOT EXISTS audio_tts_url VARCHAR"))
                conn.commit()
                print("Column added successfully.")
        except Exception as e:
            print(f"Error adding column: {e}")
            sys.exit(1)
    else:
        print("Column 'audio_tts_url' already exists.")
    
    # Verify
    columns = [col['name'] for col in inspector.get_columns('drills')]
    print("Updated columns:", columns)

if __name__ == "__main__":
    check_and_fix()
