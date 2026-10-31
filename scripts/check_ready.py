#!/usr/bin/env python3
"""Read-only presentation preflight; never starts daemons or downloads models."""

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import sqlite3
import sys
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPENDENCIES = ("ollama", "sentence-transformers", "sqlite-vec", "pypdf", "python-docx", "numpy", "psutil", "torch")


def check_database(db_path: str) -> tuple[bool, str]:
    """Check the corpus without creating or modifying any database."""
    if not os.path.isfile(db_path):
        return False, "Knowledge database is missing; ingest or sync documents before the presentation."
    conn = None
    try:
        conn = sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
        count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        if not count:
            return False, "Knowledge database has no chunks; ingest documents first."
        return True, f"Knowledge database contains {count} chunks."
    except sqlite3.Error:
        return False, "Knowledge database is unreadable or its chunks table is missing."
    finally:
        if conn is not None:
            conn.close()


def check_ollama(host: str) -> tuple[bool, str]:
    """Check installed models without loading one into RAM."""
    if "://" not in host:
        host = "http://" + host
    try:
        with urllib.request.urlopen(host.rstrip("/") + "/api/tags", timeout=3) as response:
            payload = json.load(response)
        models = [model.get("name") or model.get("model") for model in payload.get("models", [])]
        models = [model for model in models if isinstance(model, str) and model]
        if not models:
            return False, "Ollama is reachable but has no installed models."
        selected = os.getenv("RAG_MODEL")
        if selected and selected not in models:
            return False, "Selected RAG_MODEL is not installed. Choose an installed model; no download was started."
        return True, "Ollama is reachable with installed models: " + ", ".join(models)
    except (OSError, ValueError, TypeError, AttributeError):
        return False, "Ollama is unavailable. Start ollama serve in a separate terminal when needed."


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui-only", action="store_true", help="Do not require Ollama for a UI-only presentation")
    args = parser.parse_args()
    results = []
    for dependency in DEPENDENCIES:
        try:
            version = importlib.metadata.version(dependency)
            results.append((True, f"{dependency} {version}"))
        except importlib.metadata.PackageNotFoundError:
            results.append((False, f"Missing dependency: {dependency}. Use this project's venv and requirements.txt."))
    results.append(check_database(os.path.join(BASE_DIR, "data", "vectors.db")))
    if args.ui_only:
        print("UI ONLY: model answers are not checked or claimed ready.")
    else:
        results.append(check_ollama(os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")))
    for ok, message in results:
        print(f"{'PASS' if ok else 'FAIL'}: {message}")
    print("Embedding/reranker caches and actual model answers still require a rehearsal query.")
    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
