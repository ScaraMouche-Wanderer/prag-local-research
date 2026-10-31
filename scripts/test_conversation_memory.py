#!/usr/bin/env python3
"""
Test script to verify multi-turn conversational memory and query contextualization in PRAG.
"""

import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from pipeline import run_pipeline, contextualize_query_from_history
from answer import get_best_available_model

DB_PATH = os.path.join(BASE_DIR, "data", "vectors.db")

def test_contextualization():
    print("[TEST 1] Contextualize query with referential pronoun...")
    history = [
        {"role": "user", "content": "What is the Nmap security scanner?"},
        {"role": "assistant", "content": "Nmap is an open-source network exploration and security auditing tool."}
    ]
    follow_up = "How do I run a stealth SYN scan with it?"
    contextualized = contextualize_query_from_history(follow_up, history)
    print(f"Original: {follow_up}")
    print(f"Contextualized: {contextualized}")
    assert "nmap" in contextualized.lower(), "Contextualized query should contain 'nmap'"
    print("✓ Contextualization test passed!")

def test_pipeline_multiturn():
    print("\n[TEST 2] Pipeline multi-turn execution...")
    model = get_best_available_model()
    print(f"Using model: {model}")

    # Turn 1
    q1 = "What is Nmap?"
    print(f"\nTurn 1 Question: {q1}")
    res1 = run_pipeline(
        question=q1,
        base_dir=BASE_DIR,
        db_path=DB_PATH,
        model_name=model,
        top_k=2
    )
    a1 = res1["parsed"]["answer_text"] or res1["raw_answer"]
    print(f"Turn 1 Answer (first 120 chars): {a1[:120]}...")
    assert len(a1) > 20, "Turn 1 answer should not be empty"

    history = [
        {"role": "user", "content": q1},
        {"role": "assistant", "content": a1}
    ]

    # Turn 2: Follow-up using referential pronoun
    q2 = "What command syntax does it use to scan TCP ports 80 and 443?"
    print(f"\nTurn 2 Question: {q2}")
    res2 = run_pipeline(
        question=q2,
        base_dir=BASE_DIR,
        db_path=DB_PATH,
        model_name=model,
        top_k=2,
        history=history
    )
    a2 = res2["parsed"]["answer_text"] or res2["raw_answer"]
    print(f"Turn 2 Answer (first 160 chars): {a2[:160]}...")
    assert ("80" in a2 or "443" in a2 or "nmap" in a2.lower() or "-p" in a2), "Turn 2 should recognize Nmap context and port syntax"
    print("✓ Pipeline multi-turn test passed!")

if __name__ == "__main__":
    test_contextualization()
    test_pipeline_multiturn()
    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
