import sqlite3
import os

db_path = "/home/ubuntu/CodingAgentBot/coderagent.db"

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN language VARCHAR(10) DEFAULT 'en-US';")
        conn.commit()
        print("✅ Successfully added 'language' column to 'users' table.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("ℹ️ 'language' column already exists.")
        else:
            print(f"❌ Error: {e}")
    finally:
        conn.close()
else:
    print("ℹ️ Database file not found. It will be created with the new schema on next bot start.")
