#!/usr/bin/env python3
"""
SQLite database storage & vector embedding layer using sqlite-vec and sentence-transformers.
Supports 768-dimensional BAAI/bge-base-en-v1.5 embeddings and multi-corpus source_type tagging.
"""

import os
import sqlite3

EMBEDDING_DIM = 768

_EMBEDDER_INSTANCE = None
_RERANKER_INSTANCE = None


def get_embedder():
    """Returns a cached singleton SentenceTransformer embedder instance."""
    global _EMBEDDER_INSTANCE
    if _EMBEDDER_INSTANCE is None:
        from sentence_transformers import SentenceTransformer
        _EMBEDDER_INSTANCE = SentenceTransformer("BAAI/bge-base-en-v1.5", device="cpu")
    return _EMBEDDER_INSTANCE


def get_reranker():
    """Returns a cached singleton CrossEncoder reranker instance."""
    global _RERANKER_INSTANCE
    if _RERANKER_INSTANCE is None:
        from sentence_transformers import CrossEncoder
        _RERANKER_INSTANCE = CrossEncoder("BAAI/bge-reranker-base", device="cpu")
    return _RERANKER_INSTANCE


def get_db_connection(db_path: str):
    import sqlite_vec
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA journal_mode=WAL;")
    db.execute("PRAGMA synchronous=NORMAL;")
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    db.enable_load_extension(False)
    return db

def init_db(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = get_db_connection(db_path)
    cursor = db.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_hashes (
            file_path TEXT PRIMARY KEY,
            file_hash TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kali_sources (
            tool_name TEXT PRIMARY KEY,
            last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_hash TEXT,
            doc_version TEXT DEFAULT 'local_man'
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            file_hash TEXT,
            file_type TEXT,
            page_number INTEGER,
            chunk_index INTEGER,
            chunk_text TEXT,
            source_type TEXT DEFAULT 'local_file'
        );
    """)

    cursor.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vectors USING vec0(
            embedding float[{EMBEDDING_DIM}]
        );
    """)

    db.commit()
    db.close()

def get_stored_file_hash(db_path: str, file_path: str) -> str:
    db = get_db_connection(db_path)
    cursor = db.cursor()
    cursor.execute("SELECT file_hash FROM file_hashes WHERE file_path = ?", (file_path,))
    row = cursor.fetchone()
    db.close()
    return row[0] if row else None

def remove_existing_file_records(db_path: str, file_path: str):
    """Remove chunks and vectors associated with a specific file path before re-indexing."""
    db = get_db_connection(db_path)
    cursor = db.cursor()
    
    cursor.execute("SELECT id FROM chunks WHERE file_path = ?", (file_path,))
    chunk_ids = [row[0] for row in cursor.fetchall()]
    
    if chunk_ids:
        placeholders = ",".join("?" * len(chunk_ids))
        cursor.execute(f"DELETE FROM chunk_vectors WHERE rowid IN ({placeholders})", chunk_ids)
        cursor.execute(f"DELETE FROM chunks WHERE id IN ({placeholders})", chunk_ids)
    
    cursor.execute("DELETE FROM file_hashes WHERE file_path = ?", (file_path,))
    db.commit()
    db.close()

def store_chunks_and_embeddings(db_path: str, file_path: str, file_hash: str, chunks_data: list[dict], embedder, source_type: str = 'local_file'):
    """
    Stores chunks in SQLite table and inserts corresponding 768-dim vector embeddings into sqlite-vec virtual table.
    chunks_data: list of dicts with keys: file_type, page_number, chunk_index, chunk_text
    """
    if not chunks_data:
        return 0

    import sqlite_vec

    remove_existing_file_records(db_path, file_path)

    db = get_db_connection(db_path)
    cursor = db.cursor()

    texts = [c['chunk_text'] for c in chunks_data]
    embeddings = embedder.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    inserted_count = 0
    for chunk, emb in zip(chunks_data, embeddings):
        cursor.execute("""
            INSERT INTO chunks (file_path, file_hash, file_type, page_number, chunk_index, chunk_text, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (file_path, file_hash, chunk['file_type'], chunk.get('page_number', 1), chunk['chunk_index'], chunk['chunk_text'], source_type))
        
        chunk_id = cursor.lastrowid
        tensor_bytes = sqlite_vec.serialize_float32(emb.tolist())
        
        cursor.execute("""
            INSERT INTO chunk_vectors(rowid, embedding)
            VALUES (?, ?)
        """, (chunk_id, tensor_bytes))
        
        inserted_count += 1

    cursor.execute("""
        INSERT INTO file_hashes (file_path, file_hash)
        VALUES (?, ?)
        ON CONFLICT(file_path) DO UPDATE SET file_hash=excluded.file_hash, updated_at=CURRENT_TIMESTAMP
    """, (file_path, file_hash))

    db.commit()
    db.close()
    return inserted_count
