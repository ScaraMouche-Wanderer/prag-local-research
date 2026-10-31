# Project Conventions for PRAG

> Project-specific patterns, architectural decisions, and anti-patterns that AI models must follow.

## Architecture Decisions

### Why Embedded HTML (not separate files)?
The web UI is a single Python string in `web_ui.py`. This is intentional:
- Zero build step — no webpack, no npm, no static file serving
- Single file deployment — copy one `.py` file
- No CORS issues — everything served from same origin
- Inline everything — fonts via Google Fonts CDN, icons via emoji

### Why Rule-Based Router (not LLM)?
`router.py` uses keyword matching and fuzzy logic, never an LLM call:
- Routing is a deterministic, low-latency decision
- Saves ~2-5 seconds and ~100 tokens per query
- Makes routing behavior predictable and testable
- Can be extended with new keywords without model changes

### Why SQLite-vec (not Chroma/Pinecone/Weaviate)?
- Zero daemon — just a file on disk
- Zero idle memory — loaded only during queries
- Portable — copy one `.db` file
- Fast enough for <10K chunks

## Patterns to Follow

### Pipeline Data Flow
```python
# The pipeline always returns this structure:
{
    "question": str,           # Original user question
    "route": str,              # Resolved route (kali_docs, local_file, etc.)
    "is_ambiguous": bool,      # Whether the query spans multiple domains
    "route_reason": str,       # Human-readable routing explanation
    "chunks": list[dict],      # Formatted chunks for API consumers
    "raw_chunks": list[dict],  # Raw chunks with all metadata
    "raw_answer": str,         # Unprocessed model output
    "thinking_process": str,   # Extracted <think> content
    "parsed": dict,            # Structured metadata (confidence, reason, sources)
    "conflict": dict,          # Conflict detection results
    "has_conflict": bool,      # Whether sources disagree
    "latency_ms": int,         # Total pipeline execution time
    "used_web_fallback": bool  # Whether live web was queried
}
```

### SSE Event Contract
Web UI depends on these exact event types in this order:
```
stage(route) → stage(route_done) → stage(retrieve) → stage(retrieve_done)
→ stage(rerank) → stage(rerank_done) → meta({chunks, confidence, ...})
→ stage(generate) → think(token) × N → token(token) × N
→ stage(generate_done) → done({final_payload})
```

### Chunk Format
```python
{
    "file_name": "nmap.man.txt",
    "source_type": "kali_docs",
    "tier": 1.0,
    "tier_label": "Primary Source",
    "chunk_text": "...",
    "rerank_score": 0.85,
    "distance": 0.23,
    "page_number": 1
}
```

## Anti-Patterns

### ❌ Don't Add External Build Tools
No webpack, no vite, no npm, no node_modules. If you need a JS library, load it from CDN.

### ❌ Don't Split web_ui.py Into Multiple Files
The HTML/CSS/JS is intentionally embedded. Don't extract to `static/`, `templates/`, etc.

### ❌ Don't Use Python Logging Module
Use the `logger_func` callback pattern throughout. The caller decides output destination.

### ❌ Don't Cache Web Fallback Results
Web fallback (Wikipedia/DuckDuckGo) results are ephemeral. Don't store them in the vector DB.

### ❌ Don't Add Authentication
PRAG runs locally on 127.0.0.1. No auth needed. Don't add login flows.

## Testing Checklist

Before committing changes:
1. `python main.py status` — DB and system connectivity
2. `python main.py ask "What is nmap?" -v` — full pipeline test
3. `python main.py serve` → open browser → submit a query — web UI test
4. Check no Python warnings/errors in terminal output
5. Verify `requirements.txt` if new dependencies added
