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
        table_names = []
    
    # --- Start checking 'drills' table ---
    if 'drills' not in table_names:
        print("[SCHEMA] Table 'drills' does not exist yet. It will be created by ORM. Skipping column check.")
    else:
        # Check if column exists in drills table
        try:
            columns = [col['name'] for col in inspector.get_columns('drills')]
        except Exception as e:
            print(f"[SCHEMA] Error inspecting table 'drills': {e}")
            columns = [] # Treat as empty if inspection fails
        
        print(f"[SCHEMA] Existing columns in drills: {columns}")
        
        if 'audio_tts_url' not in columns:
            print("[SCHEMA] Column 'audio_tts_url' missing. Adding...")
            try:
                with engine.connect() as conn:
                    if DATABASE_URL.startswith('sqlite'):
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
                        conn.execute(text("ALTER TABLE drills ADD COLUMN IF NOT EXISTS audio_tts_url VARCHAR"))
                        conn.commit()
                        print("[SCHEMA] Column added successfully (PostgreSQL).")
            except Exception as e:
                print(f"[SCHEMA] Error adding column: {e}")
        else:
            print("[SCHEMA] Column 'audio_tts_url' already exists.")
        
        # Verify drills table columns
        try:
            columns = [col['name'] for col in inspector.get_columns('drills')]
            print(f"[SCHEMA] Updated columns in drills: {columns}")
        except Exception as e:
            print(f"[SCHEMA] Could not verify columns: {e}")

    # --- Start checking 'tests' table ---
    if 'tests' not in table_names:
        print("[SCHEMA] Table 'tests' does not exist yet. It will be created by ORM. Skipping column check.")
    else:
        try:
            test_columns = [col['name'] for col in inspector.get_columns('tests')]
        except Exception as e:
            print(f"[SCHEMA] Error inspecting table 'tests': {e}")
            test_columns = [] # Treat as empty if inspection fails

        print(f"[SCHEMA] Existing columns in tests: {test_columns}")

        if 'video_url' not in test_columns:
            print("[SCHEMA] Column 'video_url' missing in 'tests' table. Adding...")
            try:
                with engine.connect() as conn:
                    if DATABASE_URL.startswith('sqlite'):
                        try:
                            conn.execute(text("ALTER TABLE tests ADD COLUMN video_url VARCHAR"))
                            conn.commit()
                            print("[SCHEMA] Column 'video_url' added successfully to 'tests' (SQLite).")
                        except Exception as e:
                            if 'duplicate column name' in str(e).lower():
                                print("[SCHEMA] Column 'video_url' already exists in 'tests' (SQLite).")
                            else:
                                raise
                    else:
                        conn.execute(text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS video_url VARCHAR"))
                        conn.commit()
                        print("[SCHEMA] Column 'video_url' added successfully to 'tests' (PostgreSQL).")
            except Exception as e:
                print(f"[SCHEMA] Error adding 'video_url' column to 'tests': {e}")
        else:
            print("[SCHEMA] Column 'video_url' already exists in 'tests'.")

        # Verify tests table columns
        try:
            test_columns = [col['name'] for col in inspector.get_columns('tests')]
            print(f"[SCHEMA] Updated columns in tests: {test_columns}")
        except Exception as e:
            print(f"[SCHEMA] Could not verify tests columns: {e}")

    # Check if table 'tests' exists and add 'video_url' column if missing
    if 'tests' not in table_names:
        print("[SCHEMA] Table 'tests' does not exist yet. It will be created by ORM. Skipping column check.")
    else:
        try:
            test_columns = [col['name'] for col in inspector.get_columns('tests')]
        except Exception as e:
            print(f"[SCHEMA] Error inspecting table 'tests': {e}")
            return

        print(f"[SCHEMA] Existing columns in tests: {test_columns}")

        if 'video_url' not in test_columns:
            print("[SCHEMA] Column 'video_url' missing in 'tests' table. Adding...")
            try:
                with engine.connect() as conn:
                    if DATABASE_URL.startswith('sqlite'):
                        try:
                            conn.execute(text("ALTER TABLE tests ADD COLUMN video_url VARCHAR"))
                            conn.commit()
                            print("[SCHEMA] Column 'video_url' added successfully to 'tests' (SQLite).")
                        except Exception as e:
                            if 'duplicate column name' in str(e).lower():
                                print("[SCHEMA] Column 'video_url' already exists in 'tests' (SQLite).")
                            else:
                                raise
                    else:
                        conn.execute(text("ALTER TABLE tests ADD COLUMN IF NOT EXISTS video_url VARCHAR"))
                        conn.commit()
                        print("[SCHEMA] Column 'video_url' added successfully to 'tests' (PostgreSQL).")
            except Exception as e:
                print(f"[SCHEMA] Error adding 'video_url' column to 'tests': {e}")
                return
        else:
            print("[SCHEMA] Column 'video_url' already exists in 'tests'.")

        try:
            test_columns = [col['name'] for col in inspector.get_columns('tests')]
            print(f"[SCHEMA] Updated columns in tests: {test_columns}")
        except Exception as e:
            print(f"[SCHEMA] Could not verify tests columns: {e}")

if __name__ == "__main__":
    check_and_fix()
