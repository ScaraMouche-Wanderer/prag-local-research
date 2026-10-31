#!/usr/bin/env python3
"""
Retrieval engine using 768-dim BAAI/bge-base-en-v1.5 + BAAI/bge-reranker-base CrossEncoder reranking.
Supports source_type filtering (local_file, kali_docs, or all).
"""

import gc
import os
import re
import sys
import logging
from embed_store import get_db_connection, get_embedder, get_reranker
from tier_config import get_tier


def has_exact_option_definition(question: str, text: str, file_path: str) -> bool:
    """Recognize a definition only for the named tool and one case-sensitive option."""
    flags = list(dict.fromkeys(re.findall(r"(?<!\w)--?[A-Za-z][A-Za-z0-9-]*", question)))
    tool = os.path.basename(file_path).split(".")[0]
    if len(flags) != 1 or not tool or not re.search(r"\b" + re.escape(tool) + r"\b", question, re.I):
        return False
    return bool(re.search(r"^\s*" + re.escape(flags[0]) + r"(?:\s*:\s*|\s{2,})\S", text, re.M))

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)

EMBED_MODEL_NAME = "BAAI/bge-base-en-v1.5"
RERANK_MODEL_NAME = "BAAI/bge-reranker-base"

def retrieve_top_k(query_str: str, base_dir: str, db_path: str, top_k: int = 3, candidate_k: int = 10,
                   source_type: str = "all", use_reranker: bool = True, embedder=None, reranker=None,
                   logger_func=None) -> list[dict]:
    if not query_str or not query_str.strip():
        return []

    if not os.path.exists(db_path):
        return []

    import sqlite_vec

    def _log(msg: str):
        if logger_func:
            logger_func(msg)
        elif "-v" in sys.argv or "--verbose" in sys.argv:
            print(f"\033[2m{msg}\033[0m")

    # 1. Embed query (bge-base-en-v1.5: 768 dims)
    if embedder is None:
        embedder = get_embedder()

    query_vector = embedder.encode(query_str, convert_to_numpy=True, show_progress_bar=False)
    tensor_bytes = sqlite_vec.serialize_float32(query_vector.tolist())

    # 2. Vector similarity search from SQLite
    db = get_db_connection(db_path)
    cursor = db.cursor()

    fetch_k = candidate_k if use_reranker else top_k

    if source_type != "all":
        cursor.execute("""
            SELECT c.id, c.file_path, c.file_type, c.page_number, c.chunk_index, c.chunk_text, v.distance, c.source_type
            FROM chunk_vectors v
            JOIN chunks c ON c.id = v.rowid
            WHERE c.source_type = ? AND v.embedding MATCH ? AND k = ?
            ORDER BY distance ASC;
        """, (source_type, tensor_bytes, fetch_k))
    else:
        cursor.execute("""
            SELECT c.id, c.file_path, c.file_type, c.page_number, c.chunk_index, c.chunk_text, v.distance, c.source_type
            FROM chunk_vectors v
            JOIN chunks c ON c.id = v.rowid
            WHERE v.embedding MATCH ? AND k = ?
            ORDER BY distance ASC;
        """, (tensor_bytes, fetch_k))

    rows = cursor.fetchall()

    # Semantic top-K may miss a short CLI flag. Supplement it with bounded,
    # parameterized literal lookup; keep real reranker scores unchanged.
    flags = list(dict.fromkeys(re.findall(r"(?<!\w)--?[A-Za-z][A-Za-z0-9-]*", query_str)))
    if len(flags) == 1:
        sql = """SELECT id, file_path, file_type, page_number, chunk_index,
                        chunk_text, 1.0, source_type FROM chunks
                 WHERE instr(chunk_text, ?) > 0"""
        parameters = [flags[0]]
        if source_type != "all":
            sql += " AND source_type = ?"
            parameters.append(source_type)
        sql += " ORDER BY id LIMIT 20"
        cursor.execute(sql, parameters)
        existing = {row[0] for row in rows}
        for row in cursor.fetchall():
            if row[0] not in existing and has_exact_option_definition(query_str, row[5], row[1]):
                rows.append(row)
                existing.add(row[0])

    # Fetch doc_version metadata from kali_sources
    kali_version_map = {}
    try:
        cursor.execute("SELECT tool_name, doc_version FROM kali_sources;")
        for k_tool, k_ver in cursor.fetchall():
            kali_version_map[k_tool] = k_ver
    except Exception as e:
        _log(f"[RETRIEVE WARN] Could not query kali_sources metadata: {e}")

    db.close()

    if not rows:
        return []

    candidates = []
    for row in rows:
        file_path = row[1]
        file_name = os.path.basename(file_path)
        tool_stem = os.path.splitext(file_name)[0]
        src_type = row[7]
        doc_version = kali_version_map.get(tool_stem) if (src_type == "kali_docs" or tool_stem in kali_version_map) else None
        tier_val = get_tier(src_type, doc_version=doc_version, source_name=file_name)

        candidates.append({
            'chunk_id': row[0],
            'file_path': file_path,
            'file_name': file_name,
            'file_type': row[2],
            'page_number': row[3],
            'chunk_index': row[4],
            'chunk_text': row[5],
            'distance': row[6],
            'source_type': src_type,
            'doc_version': doc_version,
            'exact_option_match': has_exact_option_definition(query_str, row[5], file_path),
            'tier': tier_val
        })

    # 3. Two-stage reranking (bge-reranker-base)
    if use_reranker and len(candidates) > 1:
        try:
            import math
            if reranker is None:
                reranker = get_reranker()

            pairs = [(query_str, c['chunk_text']) for c in candidates]
            scores = reranker.predict(pairs, show_progress_bar=False)
            
            for idx, score in enumerate(scores):
                # Sigmoid activation to normalize CrossEncoder logits to 0-1 probability
                candidates[idx]['rerank_score'] = 1.0 / (1.0 + math.exp(-float(score)))
            
            candidates.sort(key=lambda x: x['rerank_score'], reverse=True)
        except Exception as e:
            _log(f"[RETRIEVE WARN] CrossEncoder reranking failed: {e}. Falling back to vector distance order.")

    # Stable prioritization protects exact local evidence without inventing a
    # semantic score. Other candidates retain their reranker/distance order.
    candidates.sort(key=lambda item: not item["exact_option_match"])
    return candidates[:top_k]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python retrieve.py <query_string> [source_type]")
        sys.exit(1)

    query_str = sys.argv[1]
    source_type = sys.argv[2] if len(sys.argv) > 2 else "all"

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "data", "vectors.db")

    top_chunks = retrieve_top_k(query_str, base_dir, db_path, top_k=3, source_type=source_type)
    print(f"Top {len(top_chunks)} retrieved chunks for query: '{query_str}' (source_type={source_type})\n")
    for idx, c in enumerate(top_chunks, start=1):
        score_str = f"Rerank Score: {c.get('rerank_score', 0):.4f}" if 'rerank_score' in c else f"Dist: {c['distance']:.4f}"
        print(f"[{idx}] {c['file_name']} (Page {c['page_number']}, Source: {c['source_type']}, {score_str})")
        print(f"    {c['chunk_text'][:150]}...\n")
