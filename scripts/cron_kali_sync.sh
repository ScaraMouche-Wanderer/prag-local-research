#!/usr/bin/env bash
# Weekly cron script for syncing Kali/Linux documentation and re-ingesting into SQLite vector database.
# Recommended cron entry (runs every Sunday at 3:00 AM):
# 0 3 * * 0 /absolute/path/to/PRAG/scripts/cron_kali_sync.sh >> /tmp/kali_sync_cron.log 2>&1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAG_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== [$(date)] Starting Scheduled Kali Docs Sync ==="
cd "$RAG_DIR" || exit 1

"$RAG_DIR/venv/bin/python" main.py sync-kali
"$RAG_DIR/venv/bin/python" main.py ingest

echo "=== [$(date)] Scheduled Kali Docs Sync Complete ==="
