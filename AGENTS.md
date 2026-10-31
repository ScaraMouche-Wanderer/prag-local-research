# AGENTS.md — PRAG AI Context Guide

> **Purpose:** This file is automatically read by AI assistants (Antigravity, Cursor, Copilot, GitHub Copilot Workspace, etc.) to understand the project structure, conventions, and design principles. Keep it accurate and up-to-date.

---

## Project Identity

- **Name:** PRAG (Personal Research & Analysis Gateway)
- **Description:** Local-first, offline RAG (Retrieval-Augmented Generation) system for Linux, cybersecurity, and general research
- **Stack:** Python 3.10+, Ollama (local LLM), SQLite + sqlite-vec (vector DB), sentence-transformers (embeddings)
- **Primary Model:** Qwen3:8B via Ollama (local inference, no cloud)
- **Design Philosophy:** Evidence-first, local-first, zero-cloud, minimal memory footprint

---

## Architecture Overview

```
User Query → Router (rule-based) → Retrieval (SQLite-vec) → Reranking (CrossEncoder)
    → Web Fallback (if low confidence) → LLM Generation (Ollama) → Parsed Response
```

### Pipeline Stages
1. **Router** (`router.py`) — Rule-based keyword/fuzzy classification, zero LLM cost
2. **Math Engine** (`math_solver.py`) — Deterministic computation for math queries
3. **Retrieval** (`retrieve.py`) — BGE embedding → SQLite-vec cosine similarity
4. **Reranking** (`embed_store.py`) — CrossEncoder scoring (bge-reranker-base)
5. **Web Fallback** (`web_fallback.py`) — Wikipedia + DuckDuckGo when local confidence < 0.60
6. **Generation** (`answer.py`) — Ollama streaming with domain-specific system prompts
7. **Parsing** (`response_parser.py`) — Structured metadata extraction (confidence, sources, conflicts)

---

## File Map

### Core Application
| File | Purpose | Lines |
|---|---|---|
| `main.py` | CLI entry point — `ask`, `chat`, `serve`, `ingest`, `sync-kali`, `status`, `sources`, `history`, `stats`, `seed` | ~640 |
| `scripts/pipeline.py` | Shared RAG pipeline — single source of truth for query execution | ~350 |
| `scripts/web_ui.py` | Web interface (HTML/CSS/JS embedded) + HTTP server + SSE streaming | ~3450 |

### RAG Pipeline Modules
| File | Purpose |
|---|---|
| `scripts/router.py` | Rule-based query classifier with fuzzy keyword matching |
| `scripts/retrieve.py` | Two-stage retrieval: embedding search + CrossEncoder reranking |
| `scripts/answer.py` | Ollama generation with retry logic, domain prompts, streaming |
| `scripts/embed_store.py` | SQLite-vec storage, embedder/reranker singleton loaders |
| `scripts/chunker.py` | Text chunking (paragraph/sentence boundaries, 500-800 tokens) |
| `scripts/response_parser.py` | Extracts confidence, sources, conflicts from model output |
| `scripts/query_log.py` | Query history logging, feedback storage, analytics |
| `scripts/tier_config.py` | Source trust tier labels (Primary, Fallback, Secondary, Community) |
| `scripts/web_fallback.py` | Live Wikipedia + DuckDuckGo parallel fetch |
| `scripts/math_solver.py` | Deterministic math engine (AST + SymPy) |

### Ingestion & Sync
| File | Purpose |
|---|---|
| `scripts/ingest.py` | File parser (PDF, DOCX, MD, TXT) + embedding pipeline |
| `scripts/seed_knowledge.py` | Multi-domain knowledge base seeder (electronics, software, economics) |
| `scripts/sync_kali_docs.py` | Man page + tool docs sync for 72+ Linux/security tools |
| `scripts/cron_kali_sync.sh` | Cron wrapper for automated weekly Kali doc sync |

### Data & Knowledge
| Path | Contents |
|---|---|
| `data/vectors.db` | SQLite + sqlite-vec vector database (~3-7 MB) |
| `knowledge_base/` | User's local files (PDFs, Notes, Books, Documentation, Research, Projects) |
| `knowledge_base_kali/` | Auto-synced Kali/Linux tool documentation |

### Configuration & Docs
| File | Purpose |
|---|---|
| `AGENTS.md` | **This file** — AI assistant context guide |
| `CONTEXT.md` | User preferences & model-editable context |
| `README.md` | Human-readable project documentation |
| `CONTRIBUTING.md` | Contribution guide for humans and AI |
| `requirements.txt` | Python dependencies |
| `launch.sh` | One-click launcher script |

---

## Design Principles (MUST follow)

1. **Local-first, file-based.** SQLite + sqlite-vec only. No server-based vector DB. Zero idle memory.
2. **One model thinks.** Qwen3:8B (or user-selected) is the only reasoning LLM. No planner chains.
3. **Code does deterministic work.** Routing, chunking, ranking = code, not LLM decisions.
4. **Nothing bulk.** No full Wikipedia dumps. Web fallback is live + ephemeral.
5. **Evidence before answer.** Model must cite excerpts. Must say `UNKNOWN` when evidence is insufficient.
6. **Nothing runs idle.** Only Ollama daemon stays resident. Python process loads/unloads per request.
7. **Streaming-first.** All web responses use SSE streaming for perceived instant responsiveness.

---

## Coding Conventions

### Python
- **Style:** PEP 8 with relaxed line length (120 chars)
- **Type Hints:** Use for all function signatures
- **Imports:** Standard library → third-party → local modules, each separated by blank line
- **Error Handling:** Always `try/except` around DB operations and Ollama calls with `pass` on non-critical failures
- **Logging:** Use `logger_func` callback pattern (not Python logging module) — the caller decides where output goes
- **Path Construction:** Always use `os.path.join()` with `BASE_DIR` — never hardcode paths
- **Constants:** ALL_CAPS at module level

### Web UI (embedded in web_ui.py)
- **CSS:** Vanilla CSS with CSS custom properties (design tokens in `:root`)
- **JS:** Vanilla JavaScript, no frameworks
- **Fonts:** Inter (sans) + JetBrains Mono (code), loaded from Google Fonts
- **Theme:** Clean light theme as default with dark mode support
- **Responsiveness:** Mobile-first breakpoints at 768px and 480px

### API Design
- **Endpoints:** `/api/ask`, `/api/ask-stream` (SSE), `/api/status`, `/api/history`, `/api/stats`, `/api/feedback`, `/api/tools`
- **Streaming:** Server-Sent Events (SSE) with event types: `stage`, `think`, `meta`, `token`, `done`, `error`
- **Error Format:** `{"error": "message"}`

---

## Source Trust Tiers

| Tier | Trust Level | Examples |
|---|---|---|
| 1.0 | Primary | Local files, official man pages, `--help` output |
| 1.5 | Fallback | Hardcoded tool docs (tool not installed) |
| 2.0 | Secondary | Wikipedia |
| 3.0 | Community | DuckDuckGo snippets |

---

## Common Tasks

### Adding a New CLI Command
1. Add argument parser in `main.py` → `build_parser()`
2. Add handler in `main.py` → `main()` function
3. Update `README.md` usage section

### Adding a New API Endpoint
1. Add route in `web_ui.py` → `RAGRequestHandler.do_GET()` or `do_POST()`
2. Add handler method `_handle_<name>()`
3. Update `README.md` API table

### Adding a New Tool to Arsenal
1. Add entry to `SECURITY_TOOLS_CATALOG` list in `web_ui.py`
2. Add tool name to `CURATED_TOOLS` in `sync_kali_docs.py`
3. Run `python main.py sync-kali` to sync docs

### Modifying the RAG Pipeline
- All changes go through `scripts/pipeline.py` — this is the single source of truth
- Both CLI (`main.py`) and Web (`web_ui.py`) use the same pipeline
- Web UI has its own streaming variant in `_handle_ask_stream()` for SSE

---

## Anti-Patterns (DO NOT)

- ❌ Do NOT add cloud/API dependencies (OpenAI, Anthropic, etc.)
- ❌ Do NOT add heavy npm/node dependencies — web UI is embedded vanilla HTML/CSS/JS
- ❌ Do NOT use Python logging module — use the `logger_func` callback pattern
- ❌ Do NOT add background daemons beyond Ollama
- ❌ Do NOT store web fallback results permanently — they are ephemeral
- ❌ Do NOT use LLM for routing decisions — router.py is pure code
- ❌ Do NOT break the streaming SSE contract — UI depends on event types

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | Ollama API endpoint |
| `PROFILE` | `0` | Enable resource profiling when set to `1` |
| `TOKENIZERS_PARALLELISM` | `false` | Suppress HuggingFace warnings |

---

## Dependencies (keep minimal)

```
ollama              # LLM inference client
sentence-transformers  # BGE embeddings + CrossEncoder reranking
sqlite-vec          # Vector similarity search in SQLite
pypdf               # PDF text extraction
python-docx         # DOCX text extraction
numpy               # Numerical operations
psutil              # System resource monitoring
torch               # PyTorch (CPU-only build recommended)
```

---

*Last updated: 2026-09-27 | Maintained by project owner and AI assistants*

## Deployment readiness additions (2026-10-22)

- `scripts/check_ready.py`: dependency metadata, read-only corpus check and Ollama model-list preflight. No model loading.
- `scripts/test_check_ready.py`: missing/empty corpus and unavailable/model-less Ollama regressions.
- `launch.sh`: portable foreground server with cleanup, readiness, port selection and explicit UI-only mode. It no longer starts Ollama automatically.
- `DEPLOYMENT.md`: local presentation and model-rehearsal runbook.

## Evidence handling additions (2026-10-22)

- `scripts/answer.py` selects question-focused evidence windows (500 characters).
- Single-option definitions can be returned directly with their numbered source;
  conflicting definitions are not silently resolved. Empty factual evidence is UNKNOWN.
- `scripts/test_answer_evidence.py` covers CLI/streaming parity and option definitions.
- `launch.sh --model MODEL` scopes `RAG_MODEL` to the launched process; preflight
  verifies that an explicitly selected model is installed.
- `.github/workflows/checks.yml` runs lightweight tests without models or private data.

- `scripts/test_retrieve_options.py` verifies literal option lookup outside semantic top-K
  using a temporary SQLite-vec database and fake embeddings/reranker (no model downloads).
- Retrieval preserves exact named-tool definitions without inventing reranker scores;
  routing retains that local evidence instead of replacing it with web snippets.

## Explicit security source imports

- `scripts/import_security_docs.py`: resumable official documentation downloader,
  all-Kali catalogue enumeration, provenance-bearing bounded chunks and SQLite backups.
- `scripts/test_import_security_docs.py`: offline HTML, HTTPS, cache and backup regressions.
- `main.py import-security [--all-kali] [--refresh] [--ingest]` exposes the importer.
- Corpus and manifest stay ignored under `knowledge_base/` and `data/`; source
  URLs and timestamps appear in every imported evidence chunk (`kali_docs`).
- This is deliberate user-authorized source ingestion, independent of ephemeral web fallback.
