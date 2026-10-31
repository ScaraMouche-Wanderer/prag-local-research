#!/usr/bin/env python3
"""
Shared RAG Pipeline Module for Local PRAG System.
Single source of truth for the RAG execution flow:
Routing -> Mathematical Pre-computation -> Retrieval -> Web Fallback -> Rerank/Sort -> Answer Generation -> Response Parsing -> Query Logging
"""

import os
import sys
import time
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from router import classify_query_detailed, evaluate_retrieval_confidence
from retrieve import retrieve_top_k
from web_fallback import fetch_web_fallback
from answer import generate_answer, detect_potential_conflict
from tier_config import get_tier_label
from response_parser import parse_answer_metadata
from query_log import log_query, init_query_log
from embed_store import get_embedder, get_reranker
from math_solver import evaluate_math_query


def sort_key(c: dict) -> float:
    """Calculates tier-weighted rerank score sorting key."""
    tier_penalty = (c.get('tier', 1.0) - 1.0) * 0.05
    return -(c.get('rerank_score', 0.0) - tier_penalty)


def contextualize_query_from_history(question: str, history: list[dict] = None) -> str:
    """
    If the question is a short follow-up or contains pronouns/referential phrases,
    contextualizes the query with the last user query/topic for better vector & keyword retrieval.
    """
    if not history:
        return question

    q_lower = question.lower().strip()
    words = q_lower.split()

    last_user_query = ""
    for item in reversed(history):
        if item.get("role") == "user" and item.get("content"):
            last_user_query = item.get("content").strip()
            break

    if not last_user_query:
        return question

    referential_triggers = [
        "it", "its", "that", "this", "these", "those", "they", "them",
        "the tool", "the command", "the scan", "the example", "the difference",
        "first one", "second one", "third one", "above", "mentioned", "previous",
        "how about", "what about", "why", "how", "flags", "options", "syntax",
        "explain more", "elaborate", "tell me more", "how do i", "how to"
    ]

    needs_context = False
    if len(words) <= 5:
        needs_context = True
    else:
        for trigger in referential_triggers:
            if re.search(r'\b' + re.escape(trigger) + r'\b', q_lower):
                needs_context = True
                break

    if needs_context:
        last_clean = re.sub(r'[\r\n]+', ' ', last_user_query).strip()
        last_snippet = " ".join(last_clean.split()[:8])
        return f"{last_snippet} {question}"

    return question


def run_pipeline(
    question: str,
    base_dir: str = None,
    db_path: str = None,
    source_type: str = None,
    model_name: str = None,
    top_k: int = 3,
    verbose: bool = False,
    profile: bool = False,
    logger_func=None,
    history: list[dict] = None
) -> dict:
    """
    Executes the full RAG pipeline and returns a structured dictionary.
    Supports multi-turn conversation memory and retrieval contextualization.
    """
    base_dir = base_dir or BASE_DIR
    db_path = db_path or os.path.join(base_dir, "data", "vectors.db")

    def _log(msg: str):
        if logger_func:
            logger_func(msg)
        elif verbose:
            print(f"\033[2m{msg}\033[0m")

    def _time_log(label: str, t0: float):
        elapsed = time.time() - t0
        msg = f"[TIMING] {label}: {elapsed:.2f}s"
        if logger_func:
            logger_func(msg)
        elif verbose:
            print(f"\033[2m{msg}\033[0m")

    start_time = time.time()

    # Step 0: Query Contextualization for follow-up questions
    retrieval_query = contextualize_query_from_history(question, history)
    if retrieval_query != question:
        _log(f"[CONTEXT] Contextualized retrieval query: '{retrieval_query}'")

    # Step 1: Query Classification
    t_route = time.time()
    if source_type is None:
        route_info = classify_query_detailed(retrieval_query, db_path, logger_func=_log)
        route = route_info["route"]
        is_ambiguous = route_info.get("is_ambiguous", False)
        route_reason = route_info.get("reason", "")
        _log(f"[ROUTER] Auto-routed query to source_type='{route}' (ambiguous={is_ambiguous}): {route_reason}")
    else:
        route = source_type
        is_ambiguous = False
        route_reason = f"Manual override source_type specified: '{route}'"
        _log(f"[ROUTER] {route_reason}")
    _time_log("query routing", t_route)

    # Step 2: Handle Nonsense Route
    if route == "nonsense":
        raw_answer = (
            "UNKNOWN\n\n"
            "Confidence: Low\n"
            "Reason: Query appears to be nonsensical or unrecognized text.\n"
            "Sources: None"
        )
        elapsed_ms = int((time.time() - start_time) * 1000)
        parsed = parse_answer_metadata(raw_answer, potential_conflict=False)
        conflict_info = {"has_conflict": False, "higher_tier": 1.0, "lower_tier": 1.0}

        try:
            init_query_log(db_path)
            log_query(
                question=question,
                route=route,
                answer=raw_answer,
                confidence=parsed.get("confidence", "Unknown"),
                chunk_count=0,
                has_conflict=False,
                used_web_fallback=False,
                latency_ms=elapsed_ms,
                db_path=db_path
            )
        except Exception:
            pass

        return {
            "question": question,
            "route": route,
            "is_ambiguous": False,
            "route_reason": route_reason,
            "chunks": [],
            "raw_chunks": [],
            "raw_answer": raw_answer,
            "thinking_process": "",
            "parsed": parsed,
            "conflict": conflict_info,
            "has_conflict": False,
            "latency_ms": elapsed_ms,
            "used_web_fallback": False
        }

    # Step 3: High-Precision Deterministic Math Engine Check
    math_eval = evaluate_math_query(question)
    if math_eval and math_eval.get("is_math"):
        _log(f"[MATH ENGINE] High-precision math solution evaluated in <1ms.")
        steps_md = "\n".join([f"- {s}" for s in math_eval.get("steps", [])])
        res_val = math_eval.get("formatted_result", "")
        
        raw_answer = (
            f"### Result: **{res_val}**\n\n"
            f"**Exact Calculation & Step-by-Step Derivation:**\n"
            f"{steps_md}\n\n"
            f"Confidence: High\n"
            f"Reason: Evaluated with exact precision via symbolic & arithmetic engine.\n"
            f"Sources: Exact Math Engine"
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        thinking = "Evaluated formula deterministically using Python/SymPy arithmetic engine to eliminate rounding and LLM hallucination errors."
        parsed = parse_answer_metadata(raw_answer, potential_conflict=False)
        parsed["thinking_process"] = thinking
        parsed["confidence"] = "High"

        try:
            init_query_log(db_path)
            log_query(
                question=question,
                route="math_code",
                answer=parsed.get("answer_text", raw_answer),
                confidence="High",
                chunk_count=0,
                has_conflict=False,
                used_web_fallback=False,
                latency_ms=elapsed_ms,
                db_path=db_path
            )
        except Exception:
            pass

        return {
            "question": question,
            "route": "math_code",
            "is_ambiguous": False,
            "route_reason": "High-precision mathematical calculation.",
            "chunks": [],
            "raw_chunks": [],
            "raw_answer": raw_answer,
            "thinking_process": thinking,
            "parsed": parsed,
            "conflict": {"has_conflict": False, "higher_tier": 1.0, "lower_tier": 1.0},
            "has_conflict": False,
            "latency_ms": elapsed_ms,
            "used_web_fallback": False
        }

    # Step 4: Retrieval for factual / corpus routes
    chunks = []
    embedder = None
    reranker = None

    corpus_routes = ("kali_docs", "local_file", "electronics", "software_eng", "economics", "all")
    if route in corpus_routes:
        embedder = get_embedder()
        reranker = get_reranker()
        _log(f"Retrieving relevant excerpts for: {retrieval_query} (source_filter={route})...")
        t_ret = time.time()
        # For specific tool route use kali_docs, for local/domain routes search all or local_file
        source_filter = route if route in ("local_file", "kali_docs") else "all"
        chunks = retrieve_top_k(retrieval_query, base_dir, db_path, top_k=top_k,
                                source_type=source_filter,
                                embedder=embedder, reranker=reranker, logger_func=_log)
        _time_log("retrieval", t_ret)

        for c in chunks:
            if 'tier' not in c:
                c['tier'] = 1.0

    # Step 5: Route-Aware Retrieval Confidence & Live Web Fallback
    used_web_fallback = False
    if route not in ("reasoning_general", "math_code"):
        confidence_info = evaluate_retrieval_confidence(chunks, route=route, question=retrieval_query, logger_func=_log)
        if confidence_info.get('route_to_web_fallback'):
            if embedder is None:
                embedder = get_embedder()
            _log(f"[FALLBACK] Local confidence low for route='{route}' — querying live Web/Wikipedia API with domain context...")
            t_fall = time.time()
            fallback_chunks = fetch_web_fallback(retrieval_query, top_k=4, embedder=embedder, route=route)
            _time_log("web fallback", t_fall)
            if fallback_chunks:
                _log(f"[FALLBACK] Retrieved {len(fallback_chunks)} live web chunks.")
                relevant_local = [c for c in chunks if c.get('rerank_score', 0) >= 0.60]
                chunks = relevant_local + fallback_chunks if relevant_local else fallback_chunks
                used_web_fallback = True

    # Step 6: Tier-weighted Rerank Sorting
    if chunks:
        chunks.sort(key=sort_key)

    # Step 7: LLM Answer Generation
    _log(f"Querying reasoning model (model={model_name or 'auto'}, domain={route})...\n")
    t_gen = time.time()
    raw_answer = generate_answer(question, chunks, model_name=model_name, route=route, history=history)
    _time_log("generation", t_gen)

    elapsed_ms = int((time.time() - start_time) * 1000)
    _time_log("total pipeline execution", start_time)

    # Step 8: Response Parsing & Conflict Detection
    potential_conflict_info = detect_potential_conflict(chunks)
    parsed = parse_answer_metadata(raw_answer, potential_conflict=potential_conflict_info["has_conflict"])
    actual_has_conflict = parsed.get("has_conflict", False)
    thinking_process = parsed.get("thinking_process", "")

    # Format chunks for API/CLI consumers
    formatted_chunks = []
    for c in chunks:
        tier_val = c.get('tier', 1.0)
        formatted_chunks.append({
            "file_name": c.get("file_name", "Unknown"),
            "source_type": c.get("source_type", "local_file"),
            "tier": tier_val,
            "tier_label": get_tier_label(tier_val),
            "chunk_text": c.get("chunk_text", ""),
            "rerank_score": c.get("rerank_score", 0.0),
            "distance": c.get("distance", 0.0),
            "page_number": c.get("page_number", 1)
        })

    # Step 9: Log Query History
    try:
        init_query_log(db_path)
        log_query(
            question=question,
            route=route,
            answer=parsed.get("answer_text", raw_answer),
            confidence=parsed.get("confidence", "High" if route in ("reasoning_general", "math_code") else "Medium"),
            chunk_count=len(chunks),
            has_conflict=actual_has_conflict,
            used_web_fallback=used_web_fallback,
            latency_ms=elapsed_ms,
            db_path=db_path
        )
    except Exception:
        pass

    return {
        "question": question,
        "route": route,
        "is_ambiguous": is_ambiguous,
        "route_reason": route_reason,
        "chunks": formatted_chunks,
        "raw_chunks": chunks,
        "raw_answer": raw_answer,
        "thinking_process": thinking_process,
        "parsed": parsed,
        "conflict": potential_conflict_info,
        "has_conflict": actual_has_conflict,
        "latency_ms": elapsed_ms,
        "used_web_fallback": used_web_fallback
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = sys.argv[1]
        res = run_pipeline(q, verbose=True)
        print(f"Route: {res['route']} (Ambiguous: {res['is_ambiguous']})")
        print(f"Latency: {res['latency_ms']}ms")
        print(f"Confidence: {res['parsed']['confidence']}")
        print(f"Conflict: {res['has_conflict']}")
        if res.get('thinking_process'):
            print(f"\n--- Thinking Process ---\n{res['thinking_process']}\n")
        print(f"Answer:\n{res['parsed']['answer_text']}")
    else:
        print("Usage: python pipeline.py \"<question>\"")
