import sqlite3
import os

def check_db():
    db_path = "backend/drills.db"
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, video_url, audio_url, image_url FROM drills ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        
        print("Last 5 drills in database:")
        for row in rows:
            print(f"ID: {row[0]}")
            print(f"  Video URL: {row[1]}")
            print(f"  Audio URL: {row[2]}")
            print(f"  Image URL: {row[3]}")
            print("-" * 20)
            
    except Exception as e:
        print(f"❌ Error querying database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_db()
