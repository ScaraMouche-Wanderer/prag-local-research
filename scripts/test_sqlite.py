#!/usr/bin/env python3
import os
import sys
import sqlite3

def main():
    try:
        import sqlite_vec
    except ImportError:
        print("Error: 'sqlite-vec' package not installed.")
        sys.exit(1)

    db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "vectors.db")

    print(f"Connecting to SQLite database at: {db_path}")
    db = sqlite3.connect(db_path)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)

    cursor = db.cursor()
    cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS test_vec USING vec0(embedding float[768]);")

    dummy_vector = [0.1] * 768
    tensor_bytes = sqlite_vec.serialize_float32(dummy_vector)

    cursor.execute("INSERT INTO test_vec(embedding) VALUES (?);", (tensor_bytes,))
    rowid = cursor.lastrowid
    db.commit()

    cursor.execute("""
        SELECT rowid, distance 
        FROM test_vec 
        WHERE embedding MATCH ? 
        ORDER BY distance 
        LIMIT 1;
    """, (tensor_bytes,))
    result = cursor.fetchone()

    print(f"Retrieved test row: rowid={result[0]}, distance={result[1]}")
    print("SQLite + sqlite-vec working (768-dim)")

    cursor.execute("DROP TABLE IF EXISTS test_vec;")
    db.commit()
    db.close()
    sys.exit(0)

if __name__ == "__main__":
    main()
