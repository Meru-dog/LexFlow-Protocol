import sqlite3
import os

db_path = "backend/lexflow.db"

if not os.path.exists(db_path):
    print(f"Error: Database file not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("Starting migration...")
    
    # Check if contracts table needs update
    cursor.execute("PRAGMA table_info(contracts)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "pdf_url" in columns:
        print("Renaming contracts.pdf_url to file_url...")
        cursor.execute("ALTER TABLE contracts RENAME COLUMN pdf_url TO file_url")
    
    if "pdf_hash" in columns:
        print("Renaming contracts.pdf_hash to file_hash...")
        cursor.execute("ALTER TABLE contracts RENAME COLUMN pdf_hash TO file_hash")

    # Check if contract_versions table needs update
    cursor.execute("PRAGMA table_info(contract_versions)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "pdf_url" in columns:
        print("Renaming contract_versions.pdf_url to file_url...")
        cursor.execute("ALTER TABLE contract_versions RENAME COLUMN pdf_url TO file_url")

    conn.commit()
    print("Migration completed successfully!")

except Exception as e:
    conn.rollback()
    print(f"Migration failed: {e}")

finally:
    conn.close()
