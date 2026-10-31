#!/usr/bin/env python3
"""
File ingestion script for local RAG knowledge base.
Parses PDFs, DOCX, MD, and TXT files, tracks SHA-256 hashes, splits text, and embeds into SQLite.
Supports custom target directories and source_type tagging.
"""

import gc
import os
import sys
import hashlib
from chunker import chunk_text
from embed_store import init_db, get_stored_file_hash, store_chunks_and_embeddings, get_embedder

SUPPORTED_EXTENSIONS = {
    # Documents
    '.pdf', '.docx', '.md', '.txt', '.rst',
    # Code files
    '.py', '.c', '.cpp', '.h', '.ino', '.v', '.vhd',
    # Data & config
    '.json', '.yaml', '.yml', '.csv',
    # Web
    '.html',
}
EMBED_MODEL_NAME = "BAAI/bge-base-en-v1.5"

def compute_file_hash(file_path: str) -> str:
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def parse_pdf(file_path: str) -> list[tuple[int, str]]:
    """Returns list of (page_number, page_text) tuples."""
    import pypdf
    pages = []
    reader = pypdf.PdfReader(file_path)
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append((idx, text))
    return pages

def parse_docx(file_path: str) -> list[tuple[int, str]]:
    """Returns list of (page_number, text) for docx (page=1 default)."""
    import docx
    doc = docx.Document(file_path)
    full_text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    return [(1, full_text)] if full_text.strip() else []

def parse_text(file_path: str) -> list[tuple[int, str]]:
    """Returns list of (page_number, text) for txt/md files (page=1 default)."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    return [(1, text)] if text.strip() else []

def process_file(file_path: str) -> list[dict]:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        parsed_pages = parse_pdf(file_path)
    elif ext == '.docx':
        parsed_pages = parse_docx(file_path)
    elif ext in ('.md', '.txt', '.rst', '.py', '.c', '.cpp', '.h', '.ino',
                  '.v', '.vhd', '.json', '.yaml', '.yml', '.csv', '.html'):
        parsed_pages = parse_text(file_path)
    else:
        return []

    chunks_data = []
    global_chunk_idx = 0

    for page_num, page_text in parsed_pages:
        sub_chunks = chunk_text(page_text)
        for sub_chunk in sub_chunks:
            chunks_data.append({
                'file_type': ext[1:],
                'page_number': page_num,
                'chunk_index': global_chunk_idx,
                'chunk_text': sub_chunk
            })
            global_chunk_idx += 1

    return chunks_data

def run_ingestion(base_dir: str, db_path: str, target_sub_dir: str = "knowledge_base", source_type: str = "local_file"):
    kb_dir = os.path.join(base_dir, target_sub_dir) if not os.path.isabs(target_sub_dir) else target_sub_dir
    init_db(db_path)

    if not os.path.exists(kb_dir):
        print(f"Directory {kb_dir} does not exist.")
        return

    file_paths = []
    for root, _, files in os.walk(kb_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                file_paths.append(os.path.join(root, f))

    if not file_paths:
        print(f"No supported files found under {kb_dir}")
        return

    print(f"Found {len(file_paths)} candidate files in {kb_dir} (source_type={source_type})")

    embedder = None
    ingested_count = 0
    skipped_count = 0
    failed_count = 0

    for file_path in file_paths:
        try:
            rel_path = os.path.relpath(file_path, base_dir)
            current_hash = compute_file_hash(file_path)
            stored_hash = get_stored_file_hash(db_path, rel_path)

            if stored_hash == current_hash:
                print(f"[SKIPPED (Unchanged)] {rel_path}")
                skipped_count += 1
                continue

            print(f"[INGESTING] {rel_path} ...")
            chunks = process_file(file_path)
            if not chunks:
                print(f"  -> No readable text found in {rel_path}")
                failed_count += 1
                continue

            if embedder is None:
                embedder = get_embedder()

            num_inserted = store_chunks_and_embeddings(db_path, rel_path, current_hash, chunks, embedder, source_type=source_type)
            print(f"  -> Generated & stored {num_inserted} chunks.")
            ingested_count += 1

        except Exception as e:
            print(f"[FAILED] {file_path}: {e}")
            failed_count += 1

    print("\n--- Ingestion Summary ---")
    print(f"Target Dir:  {target_sub_dir}")
    print(f"Source Type: {source_type}")
    print(f"Ingested:    {ingested_count}")
    print(f"Skipped:     {skipped_count}")
    print(f"Failed:      {failed_count}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "data", "vectors.db")
    run_ingestion(base_dir, db_path)
