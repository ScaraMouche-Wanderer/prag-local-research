# Coding Standards for PRAG

> These rules apply to all AI-assisted code modifications in the PRAG project.

## Python Style

- Follow PEP 8 with 120-character line length
- Use type hints for all function signatures: `def foo(bar: str, baz: int = 5) -> dict:`
- Use f-strings for string formatting, never `.format()` or `%`
- Prefer list comprehensions over `map()`/`filter()` for readability
- Always handle `BrokenPipeError` and `ConnectionResetError` in network/streaming code

## Import Order

```python
# 1. Standard library
import os
import sys
import json

# 2. Third-party
import ollama
import numpy as np

# 3. Local modules
from router import classify_query_detailed
from retrieve import retrieve_top_k
```

## Error Handling Pattern

```python
# For non-critical operations (DB logging, status checks):
try:
    some_operation()
except Exception:
    pass

# For critical operations (pipeline, generation):
try:
    result = critical_operation()
except SpecificError as e:
    logger_func(f"[ERROR] {e}")
    # return graceful fallback
```

## Database Operations

- Always use `os.path.join(BASE_DIR, "data", "vectors.db")` for DB path
- Always call `init_query_log(db_path)` before logging
- Use `sqlite3.connect()` with explicit `conn.close()` — no context managers in hot paths
- Wrap all DB reads in try/except — the table might not exist yet

## Web UI Rules

- All HTML/CSS/JS lives inside `web_ui.py` as a single `HTML_PAGE` string
- Use CSS custom properties for ALL colors — never hardcode hex in element styles
- All interactive elements must have unique IDs
- All buttons must have `title` attributes for accessibility
- Toast notifications for all user actions (copy, feedback, errors)

## Naming Conventions

- **Python files:** `snake_case.py`
- **Python functions:** `snake_case()`
- **Python classes:** `PascalCase`
- **Constants:** `ALL_CAPS`
- **CSS classes:** `kebab-case`
- **JS functions:** `camelCase()`
- **HTML IDs:** `camelCase`
- **API endpoints:** `/api/kebab-case`

## Performance Rules

- Never load embedding model at import time — load on first use only
- Always pass shared `embedder` and `reranker` through the pipeline
- Keep Ollama model alive with `keep_alive="30m"`
- Use `ThreadPoolExecutor` for parallel I/O operations
- Trim chunk text to 500 chars in prompts to reduce token count

## Security Rules

- Never expose the server on `0.0.0.0` — bind to `127.0.0.1` only
- Sanitize all user input displayed in HTML (use `escapeHtml()`)
- No file path traversal in API endpoints
- No eval/exec on user input
