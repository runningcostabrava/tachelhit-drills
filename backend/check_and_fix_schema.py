"""
Script to check and fix missing columns in the database schema.
Run this manually when deploying or after schema changes.
"""
import sys
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import ProgrammingError, OperationalError

def mask_database_url(url: str) -> str:
    """Mask password in database URL for safe logging."""
    if '@' in url:
        # Replace password with ****
        parts = url.split('@')
        user_part = parts[0]
        if ':' in user_part:
            user_pass = user_part.split(':')
            if len(user_pass) >= 3:
                # postgresql://user:pass@host...
                user_pass[-1] = '****'
                masked_user_part = ':'.join(user_pass)
                return '@'.join([masked_user_part] + parts[1:])
    return url

def check_and_fix():
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///drills.db")
    masked_url = mask_database_url(DATABASE_URL)
    print(f"[SCHEMA] Checking schema for database: {masked_url}")
    
    try:
        engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 10})
    except Exception as e:
        print(f"[SCHEMA] Error creating engine: {e}")
        return
    
    inspector = inspect(engine)
    
    # Check if table exists
    try:
        table_names = inspector.get_table_names()
    except Exception as e:
        print(f"[SCHEMA] Error listing tables: {e}")
        # If we can't list tables, assume table doesn't exist
        table_names = []
    
    if 'drills' not in table_names:
        print("[SCHEMA] Table 'drills' does not exist yet. It will be created by ORM. Skipping column check.")
        return
    
    # Check if column exists in drills table
    try:
        columns = [col['name'] for col in inspector.get_columns('drills')]
    except Exception as e:
        print(f"[SCHEMA] Error inspecting table 'drills': {e}")
        # Table might have been deleted concurrently; skip
        return
    
    print(f"[SCHEMA] Existing columns in drills: {columns}")
    
    if 'audio_tts_url' not in columns:
        print("[SCHEMA] Column 'audio_tts_url' missing. Adding...")
        try:
            with engine.connect() as conn:
                if DATABASE_URL.startswith('sqlite'):
                    # SQLite doesn't support ADD COLUMN IF NOT EXISTS directly
                    # We'll attempt to add and ignore error if already exists
                    try:
                        conn.execute(text("ALTER TABLE drills ADD COLUMN audio_tts_url VARCHAR"))
                        conn.commit()
                        print("[SCHEMA] Column added successfully (SQLite).")
                    except Exception as e:
                        if 'duplicate column name' in str(e).lower():
                            print("[SCHEMA] Column already exists (SQLite).")
                        else:
                            raise
                else:
                    # PostgreSQL / other
                    # Use IF NOT EXISTS to avoid errors
                    conn.execute(text("ALTER TABLE drills ADD COLUMN IF NOT EXISTS audio_tts_url VARCHAR"))
                    conn.commit()
                    print("[SCHEMA] Column added successfully (PostgreSQL).")
        except Exception as e:
            print(f"[SCHEMA] Error adding column: {e}")
            # Don't exit with error; just log
            return
    else:
        print("[SCHEMA] Column 'audio_tts_url' already exists.")
    
    # Verify
    try:
        columns = [col['name'] for col in inspector.get_columns('drills')]
        print(f"[SCHEMA] Updated columns in drills: {columns}")
    except Exception as e:
        print(f"[SCHEMA] Could not verify columns: {e}")

if __name__ == "__main__":
    check_and_fix()
