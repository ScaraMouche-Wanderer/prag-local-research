#!/usr/bin/env python3
"""
Live Web and Wikipedia fallback module for Local Fact-Grounded RAG System.
Fetches high-accuracy live search results via DDGS and Wikipedia API.
Processes text strictly in-memory (chunking, embedding, scoring) with ZERO DB persistence.
"""

import os
import sys
import gc
import json
import urllib.parse
import urllib.request
import re

import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import logging

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)

from chunker import chunk_text
from tier_config import get_tier
from embed_store import get_embedder

USER_AGENT = "LocalPRAG-RAGSystem/2.0 (Linux; Fact-Grounded Research Engine)"
EMBED_MODEL_NAME = "BAAI/bge-base-en-v1.5"
RERANK_MODEL_NAME = "BAAI/bge-reranker-base"


def http_get_json(url: str, timeout: float = 4.0) -> dict:
    """Helper to execute HTTP GET and parse JSON with User-Agent header."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status == 200:
            data = response.read().decode("utf-8")
            return json.loads(data)
    return {}


def fetch_ddgs_web_search(query_str: str, max_results: int = 4) -> list[dict]:
    """
    Fetches real-time web search results and snippets via DDGS.
    """
    results = []
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query_str, max_results=max_results))
            for item in raw_results:
                title = item.get("title", "").strip()
                body = item.get("body", "").strip()
                href = item.get("href", "").strip()

                if title and body:
                    results.append({
                        "title": title,
                        "extract": f"{title}\n\n{body}",
                        "url": href,
                        "source": f"Web Search ({title[:30]})",
                        "tier": 3
                    })
    except Exception as e:
        print(f"[WARN] DDGS web search query failed: {e}")

    return results


def fetch_wikipedia_extract(query_str: str) -> list[dict]:
    """
    Queries Wikipedia Generator Search API for candidate title matches and returns extract dicts.
    """
    try:
        clean_query = re.sub(r'^(what is|what are|how to|tell me about|who is|where is|why is|which is)\s+', '', query_str, flags=re.IGNORECASE).strip()
        url = f"https://en.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(clean_query)}&gsrlimit=5&prop=extracts|info&inprop=url&exintro=1&explaintext=1&format=json&utf8=1"
        data = http_get_json(url)
        pages = data.get("query", {}).get("pages", {})

        if not pages:
            return []

        results = []
        for pid, p in sorted(pages.items(), key=lambda x: x[1].get("index", 99)):
            title = p.get("title", "")
            extract = p.get("extract", "").strip()
            page_url = p.get("fullurl", f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}")

            if not title or "disambiguation" in title.lower() or "portal:" in title.lower():
                continue

            if extract:
                results.append({
                    "title": title,
                    "extract": extract,
                    "url": page_url,
                    "source": f"Wikipedia ({title})",
                    "tier": 2
                })
                if len(results) >= 3:
                    break

        return results
    except Exception as e:
        print(f"[WARN] Wikipedia API query failed: {e}")
        return []


# Domain-specific search query prefixes for better web results
DOMAIN_SEARCH_CONTEXT = {
    'electronics': 'electronics engineering',
    'software_eng': 'software engineering',
    'economics': 'economics finance',
    'kali_docs': 'linux security cybersecurity',
}


def fetch_web_fallback(query_str: str, top_k: int = 4, embedder=None, route: str = None) -> list[dict]:
    """
    Fetches live web search and Wikipedia extracts, chunks and embeds them in memory,
    and returns top_k ranked fallback chunks.
    Uses route-based domain context for more relevant search results.
    STRICTLY IN-MEMORY: ZERO database persistence.
    """
    sources_data = []

    # Enhance search query with domain context for better results
    search_query = query_str
    if route and route in DOMAIN_SEARCH_CONTEXT:
        search_query = f"{DOMAIN_SEARCH_CONTEXT[route]} {query_str}"

    # 1. Fetch live extracts — parallel I/O for DDGS + Wikipedia
    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(fetch_ddgs_web_search, search_query, 4): "ddgs",
            executor.submit(fetch_wikipedia_extract, query_str): "wikipedia"
        }
        for future in as_completed(futures):
            try:
                res_list = future.result(timeout=6)
                if isinstance(res_list, list):
                    sources_data.extend(res_list)
            except Exception:
                pass

    if not sources_data:
        return []

    # 2. In-memory chunking
    raw_chunks = []
    for src in sources_data:
        text_chunks = chunk_text(src["extract"], chunk_size_chars=800, overlap_chars=80)
        for idx, t_chunk in enumerate(text_chunks):
            raw_chunks.append({
                'chunk_id': -1,
                'file_path': f"web_fallback/{src['source']}",
                'file_name': src['source'],
                'file_type': 'web',
                'page_number': 1,
                'chunk_index': idx,
                'chunk_text': t_chunk,
                'source_type': 'web_fallback',
                'doc_version': 'live_api',
                'tier': src.get('tier', 3.0),
                'url': src.get('url', '')
            })

    if not raw_chunks:
        return []

    # 3. In-memory embedding & scoring using SentenceTransformer
    try:
        if embedder is None:
            embedder = get_embedder()

        query_emb = embedder.encode(query_str, convert_to_numpy=True, show_progress_bar=False)
        chunk_texts = [c['chunk_text'] for c in raw_chunks]
        chunk_embs = embedder.encode(chunk_texts, convert_to_numpy=True, show_progress_bar=False)

        # Compute Cosine Similarities
        query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-9)
        chunk_norms = chunk_embs / (np.linalg.norm(chunk_embs, axis=1, keepdims=True) + 1e-9)
        similarities = np.dot(chunk_norms, query_norm)

        for idx, sim in enumerate(similarities):
            raw_chunks[idx]['rerank_score'] = float(sim)

        raw_chunks.sort(key=lambda x: x['rerank_score'], reverse=True)
    except Exception as e:
        print(f"[WARN] In-memory scoring failed: {e}")

    return raw_chunks[:top_k]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python web_fallback.py \"<query>\"")
        sys.exit(1)

    query = sys.argv[1]
    results = fetch_web_fallback(query)
    print(f"Retrieved {len(results)} fallback chunks for '{query}':\n")
    for r in results:
        print(f"- {r['file_name']} [Score: {r.get('rerank_score', 0):.4f}, Tier: {r['tier']}]")
        print(f"  {r['chunk_text'][:150]}...\n")
