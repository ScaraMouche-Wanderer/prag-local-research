#!/usr/bin/env python3
"""
Query history and session logging module for Local PRAG System.
Stores query history in the same vectors.db SQLite database.
Provides logging, retrieval, feedback tracking, and statistics functions.
"""

import os
import sys
import time
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "vectors.db")


def init_query_log(db_path: str = None):
    """Creates the query_log table if it doesn't exist."""
    db_path = db_path or DB_PATH
    if not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS query_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            route TEXT,
            answer TEXT,
            confidence TEXT,
            chunk_count INTEGER DEFAULT 0,
            has_conflict INTEGER DEFAULT 0,
            used_web_fallback INTEGER DEFAULT 0,
            latency_ms INTEGER,
            feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Try adding feedback column if table already exists without it
    try:
        conn.execute("ALTER TABLE query_log ADD COLUMN feedback TEXT;")
    except Exception:
        pass
    conn.commit()
    conn.close()


def log_query(question: str, route: str, answer: str, confidence: str = "Unknown",
              chunk_count: int = 0, has_conflict: bool = False,
              used_web_fallback: bool = False, latency_ms: int = 0,
              db_path: str = None) -> int:
    """Logs a completed query to the database and returns its ID."""
    db_path = db_path or DB_PATH
    try:
        init_query_log(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO query_log (question, route, answer, confidence, chunk_count,
                                   has_conflict, used_web_fallback, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (question, route, answer, confidence, chunk_count,
              int(has_conflict), int(used_web_fallback), latency_ms))
        last_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return last_id
    except Exception as e:
        print(f"[WARN] Failed to log query: {e}")
        return -1


def save_feedback(question: str, feedback: str, db_path: str = None) -> bool:
    """Saves user rating feedback (positive/negative) for the most recent matching query."""
    db_path = db_path or DB_PATH
    try:
        init_query_log(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE query_log
            SET feedback = ?
            WHERE id = (
                SELECT id FROM query_log
                WHERE question = ?
                ORDER BY created_at DESC
                LIMIT 1
            )
        """, (feedback, question))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[WARN] Failed to save feedback: {e}")
        return False


def get_recent_queries(limit: int = 20, db_path: str = None) -> list[dict]:
    """Returns the most recent queries."""
    db_path = db_path or DB_PATH
    try:
        init_query_log(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, question, route, confidence, chunk_count, has_conflict,
                   used_web_fallback, latency_ms, feedback, created_at
            FROM query_log
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception:
        return []


def get_query_stats(db_path: str = None) -> dict:
    """Returns aggregate statistics about query history."""
    db_path = db_path or DB_PATH
    try:
        init_query_log(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM query_log")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(latency_ms) FROM query_log WHERE latency_ms > 0")
        avg_latency = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM query_log WHERE used_web_fallback = 1")
        web_fallback_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM query_log WHERE has_conflict = 1")
        conflict_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT confidence, COUNT(*) as cnt
            FROM query_log
            GROUP BY confidence
            ORDER BY cnt DESC
        """)
        confidence_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("""
            SELECT route, COUNT(*) as cnt
            FROM query_log
            GROUP BY route
            ORDER BY cnt DESC
        """)
        route_dist = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "total_queries": total,
            "avg_latency_ms": round(avg_latency),
            "web_fallback_count": web_fallback_count,
            "conflict_count": conflict_count,
            "confidence_distribution": confidence_dist,
            "route_distribution": route_dist
        }
    except Exception:
        return {"total_queries": 0, "avg_latency_ms": 0, "web_fallback_count": 0,
                "conflict_count": 0, "confidence_distribution": {}, "route_distribution": {}}


if __name__ == "__main__":
    init_query_log()
    print("Query log table initialized.")
    stats = get_query_stats()
    print(f"Total queries: {stats['total_queries']}")
    print(f"Avg latency: {stats['avg_latency_ms']}ms")
