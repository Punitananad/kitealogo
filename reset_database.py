"""
Reset database - removes CHECK constraints that were causing issues
"""
import os
import sqlite3

DB_PATH = 'trading_zones.db'

# Backup old database
if os.path.exists(DB_PATH):
    import shutil
    backup_path = f"{DB_PATH}.backup"
    shutil.copy(DB_PATH, backup_path)
    print(f"✓ Backed up database to {backup_path}")
    
    # Remove old database
    os.remove(DB_PATH)
    print(f"✓ Removed old database")

# Create new database with updated schema
with open('database/schema.sql', 'r') as f:
    schema = f.read()

conn = sqlite3.connect(DB_PATH)
conn.executescript(schema)
conn.commit()
conn.close()

print(f"✓ Created new database: {DB_PATH}")
print("✓ Database reset complete!")
print("\nYou can now run: python app.py")
