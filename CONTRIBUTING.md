# Contributing to PRAG

> Guide for both human developers and AI assistants working on this project.

## Quick Start

```bash
cd /absolute/path/to/PRAG
source venv/bin/activate
python main.py status          # Check system health
python main.py serve           # Launch web UI at http://127.0.0.1:8000
```

## For AI Assistants

Before making changes, always read:
1. [`AGENTS.md`](./AGENTS.md) — Full project architecture and file map
2. [`CONTEXT.md`](./CONTEXT.md) — User preferences and learned patterns
3. [`.agents/rules/coding_standards.md`](./.agents/rules/coding_standards.md) — Code style rules
4. [`.agents/rules/project_conventions.md`](./.agents/rules/project_conventions.md) — Architectural patterns

After making changes:
1. Update `AGENTS.md` if you modified the file map or architecture
2. Update `CONTEXT.md` if you learned new user preferences
3. Test with `python main.py status` and `python main.py ask "test query" -v`

## Project Structure

```
PRAG/
├── rag-system/
│   ├── AGENTS.md              # AI context guide (read first!)
│   ├── CONTEXT.md             # User preferences (model-editable)
│   ├── CONTRIBUTING.md        # This file
│   ├── README.md              # Human documentation
│   ├── main.py                # CLI entry point
│   ├── requirements.txt       # Python dependencies
│   ├── launch.sh              # One-click launcher
│   ├── .agents/               # AI assistant configuration
│   │   └── rules/
│   │       ├── coding_standards.md
│   │       └── project_conventions.md
│   ├── data/                  # Vector database
│   ├── knowledge_base/        # User's local files
│   ├── knowledge_base_kali/   # Auto-synced tool docs
│   └── scripts/               # All Python modules
├── PERFORMANCE.md             # Benchmarks
└── local-rag-roadmap.md       # Build roadmap
```

## How to Add Features

### New CLI Command
1. Add parser to `build_parser()` in `main.py`
2. Add handler in `main()` function
3. Document in `README.md`

### New API Endpoint
1. Add route handling in `RAGRequestHandler` in `web_ui.py`
2. Create handler method `_handle_<name>()`
3. Document in `README.md` API table

### New Knowledge Domain
1. Add keyword set in `router.py` (e.g., `NEW_DOMAIN_KEYWORDS`)
2. Add domain system prompt in `answer.py` → `DOMAIN_SYSTEM_PROMPTS`
3. Add source type handling in `pipeline.py`
4. Seed initial knowledge with `seed_knowledge.py`

### New Security Tool
1. Add to `SECURITY_TOOLS_CATALOG` in `web_ui.py`
2. Add tool name to `CURATED_TOOLS` in `sync_kali_docs.py`
3. Run `python main.py sync-kali`

## Design Principles

1. **Local-first** — No cloud dependencies
2. **Evidence-first** — Always cite sources
3. **Minimal** — No heavy frameworks, no build steps
4. **Fast** — Streaming responses, lazy loading
5. **Honest** — Say UNKNOWN when evidence is insufficient
