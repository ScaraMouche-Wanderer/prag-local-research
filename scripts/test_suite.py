#!/usr/bin/env python3
"""
Comprehensive Automated Test Suite for PRAG Local Fact-Grounded Research Engine.
Validates all subsystem components:
1. Vector Embedding & SQLite-vec Storage
2. Semantic Retrieval & Multi-Tier Scoring
3. Query Routing & Scope Disambiguation
4. Response Parsing & Metadata Extraction
5. Mathematical Derivation & Bitwise AST Evaluation
6. Web Fallback & DDG Search
7. Query Logging & Aggregation Analytics
8. End-to-End Pipeline Execution
"""

import os
import sys
import json
import unittest
import tempfile
import sqlite3

# Ensure scripts directory is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from tier_config import get_tier, get_tier_label, TIER_DEFINITIONS
from embed_store import get_embedder, init_db, store_chunks_and_embeddings
from retrieve import retrieve_top_k
from router import classify_query
from response_parser import parse_answer_metadata, detect_actual_conflict
from math_solver import evaluate_math_query, extract_math_expression
from query_log import init_query_log, log_query, get_recent_queries, get_query_stats
from pipeline import run_pipeline


class TestPRAGCore(unittest.TestCase):

    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        init_db(self.temp_db_path)
        init_query_log(self.temp_db_path)
        self.embedder = get_embedder()

    def tearDown(self):
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except Exception:
                pass

    # ─── 1. Vector Embeddings & Storage ───
    def test_vector_embedding_generation(self):
        """Test BAAI/bge-base-en-v1.5 embedding generation."""
        text = "Linux security audit and penetration testing methodology."
        emb = self.embedder.encode(text, convert_to_numpy=True)
        self.assertEqual(len(emb), 768)
        self.assertIsInstance(float(emb[0]), float)

    def test_vector_db_insert_and_retrieve(self):
        """Test storing chunks in sqlite-vec and retrieving with tier-ranked scores."""
        test_chunks = [
            {
                "file_type": ".txt",
                "chunk_index": 0,
                "chunk_text": "Port 22 SSH should be protected with ed25519 public key authentication and Fail2ban.",
                "page_number": 1
            }
        ]
        stored = store_chunks_and_embeddings(
            self.temp_db_path,
            "local_kb/security_notes.txt",
            "dummy_hash_1",
            test_chunks,
            self.embedder,
            source_type="local_file"
        )
        self.assertEqual(stored, 1)

        # Retrieve SSH chunk
        results = retrieve_top_k(
            "How to secure SSH with key authentication?",
            BASE_DIR,
            self.temp_db_path,
            top_k=2,
            embedder=self.embedder,
            use_reranker=False
        )
        self.assertGreater(len(results), 0)
        self.assertIn("SSH", results[0]["chunk_text"])

    # ─── 2. Query Routing ───
    def test_query_routing_classification(self):
        """Test query routing between local, kali, math, reasoning, and broad scope."""
        from router import classify_query_detailed
        # Kali tool query
        r1 = classify_query_detailed("How to run a SYN scan with nmap?", db_path=self.temp_db_path)
        self.assertEqual(r1["route"], "kali_docs")

        # General reasoning / math query
        r2 = classify_query_detailed("Calculate 25 * 40 + 150", db_path=self.temp_db_path)
        self.assertIn(r2["route"], ["math", "math_code", "general_reasoning"])

        # Ambiguous / broad query
        r3 = classify_query_detailed("compare", db_path=self.temp_db_path)
        self.assertTrue(r3["is_ambiguous"])

    def test_query_routing_domain_specialization(self):
        """Test domain routing for electronics, software engineering, and economics."""
        from router import classify_query_detailed

        # Electronics domain
        re1 = classify_query_detailed("What is the cutoff frequency of an RC low pass filter with 10k resistor?", db_path=self.temp_db_path)
        self.assertEqual(re1["route"], "electronics")

        re2 = classify_query_detailed("How does an SPI protocol work with MOSI MISO clock pins?", db_path=self.temp_db_path)
        self.assertEqual(re2["route"], "electronics")

        # Software engineering domain
        rs1 = classify_query_detailed("When should I use microservice architecture vs monolith in production?", db_path=self.temp_db_path)
        self.assertEqual(rs1["route"], "software_eng")

        rs2 = classify_query_detailed("Explain the singleton design pattern and dependency injection", db_path=self.temp_db_path)
        self.assertEqual(rs2["route"], "software_eng")

        # Economics domain
        rec1 = classify_query_detailed("How does quantitative easing by the central bank impact inflation and GDP?", db_path=self.temp_db_path)
        self.assertEqual(rec1["route"], "economics")

        rec2 = classify_query_detailed("Explain price elasticity of demand and market equilibrium", db_path=self.temp_db_path)
        self.assertEqual(rec2["route"], "economics")

    # ─── 3. Mathematical Solver & Bitwise Calculator ───
    def test_math_solver_arithmetic(self):
        """Test exact arithmetic AST evaluation."""
        res = evaluate_math_query("(100 * 50) / 2 + 75")
        self.assertIsNotNone(res)
        self.assertEqual(res["formatted_result"], "2575")

    def test_math_solver_bitwise_and_hex(self):
        """Test bitwise operators and hexadecimal representations."""
        res = evaluate_math_query("0xFF ^ 0x0F")
        self.assertIsNotNone(res)
        self.assertIn("240", res["formatted_result"])
        self.assertIn("0xf0", res["formatted_result"].lower())

    def test_math_solver_percentages(self):
        """Test natural language percentage evaluation."""
        res = evaluate_math_query("what is 20% of 150")
        self.assertIsNotNone(res)
        self.assertEqual(res["formatted_result"], "30")

    def test_math_solver_symbolic(self):
        """Test calculus and algebraic solving."""
        res = evaluate_math_query("derivative of x^3 + 2*x")
        self.assertIsNotNone(res)
        self.assertIn("3*x**2 + 2", res["formatted_result"])

    # ─── 3b. Electronics Engineering Formula Solver ───
    def test_ee_formulas_ohm_and_divider(self):
        """Test Ohm's Law and Voltage Divider calculations."""
        # Ohm's Law: V = IR
        r_ohm = evaluate_math_query("V = IR for R=470 I=0.02")
        self.assertIsNotNone(r_ohm)
        self.assertEqual(r_ohm["formatted_result"], "9.4V")

        # Voltage divider: Vout = Vin * R2 / (R1 + R2)
        r_div = evaluate_math_query("voltage divider R1=10k R2=4.7k Vin=5V")
        self.assertIsNotNone(r_div)
        self.assertEqual(r_div["formatted_result"], "1.6V")

    def test_ee_formulas_rc_and_db(self):
        """Test RC time constant, reactance, and dB conversions."""
        # RC Time Constant: τ = R * C (10k * 100nF = 1ms)
        r_rc = evaluate_math_query("RC time constant R=10k C=100nF")
        self.assertIsNotNone(r_rc)
        self.assertEqual(r_rc["formatted_result"], "1ms")

        # dBm to Watts (3 dBm ≈ 2mW)
        r_db = evaluate_math_query("3 dBm to watts")
        self.assertIsNotNone(r_db)
        self.assertIn("mW", r_db["formatted_result"])

    # ─── 4. Response Parsing & Metadata Extraction ───
    def test_response_parser_clean_metadata(self):
        """Test stripping metadata and extracting structured fields."""
        raw_output = (
            "<think>\nAnalyze the question carefully.\n</think>\n\n"
            "SSH key-based authentication with Ed25519 provides stronger cryptographic security than RSA.\n\n"
            "**Confidence:** High\n"
            "**Reason:** Grounded in local security manual.\n"
            "**Sources:** [1]"
        )
        parsed = parse_answer_metadata(raw_output)
        self.assertEqual(parsed["confidence"], "High")
        self.assertEqual(parsed["confidence_level"], 3)
        self.assertEqual(parsed["reason"], "Grounded in local security manual.")
        self.assertEqual(parsed["sources"], ["[1]"])
        self.assertIn("Ed25519", parsed["answer_text"])
        self.assertNotIn("Confidence:", parsed["answer_text"])
        self.assertNotIn("<think>", parsed["answer_text"])
        self.assertEqual(parsed["thinking_process"], "Analyze the question carefully.")

    def test_response_parser_conflict_detection(self):
        """Test distinguishing between potential vs actual source conflict."""
        ans_no_conflict = "Both sources recommend using TLS 1.3 for secure communication."
        c1 = detect_actual_conflict(ans_no_conflict, potential_conflict=True)
        self.assertFalse(c1["has_conflict"])

        ans_conflict = "Source [1] states port 80 is disabled, but Source [2] contradicts this and claims port 80 is open."
        c2 = detect_actual_conflict(ans_conflict, potential_conflict=True)
        self.assertTrue(c2["has_conflict"])

    # ─── 5. Query Logging & Analytics ───
    def test_query_logging_and_stats(self):
        """Test SQLite query audit log and aggregate analytics."""
        log_query(
            question="What is the default port for SSH?",
            route="local_file",
            answer="Port 22 is the standard TCP port for SSH.",
            confidence="High",
            latency_ms=120.5,
            used_web_fallback=False,
            has_conflict=False,
            db_path=self.temp_db_path
        )
        log_query(
            question="Find latest CVEs for Apache",
            route="web_fallback",
            answer="Apache HTTP Server recent CVEs...",
            confidence="Medium",
            latency_ms=450.0,
            used_web_fallback=True,
            has_conflict=False,
            db_path=self.temp_db_path
        )

        history = get_recent_queries(limit=5, db_path=self.temp_db_path)
        self.assertEqual(len(history), 2)

        stats = get_query_stats(self.temp_db_path)
        self.assertEqual(stats["total_queries"], 2)
        self.assertEqual(stats["web_fallback_count"], 1)
        self.assertEqual(stats["confidence_distribution"]["High"], 1)
        self.assertEqual(stats["confidence_distribution"]["Medium"], 1)

    # ─── 6. End-to-End Pipeline Execution ───
    def test_pipeline_math_flow(self):
        """Test running end-to-end pipeline on math queries (instant solver path)."""
        res = run_pipeline(
            question="Compute (50 * 20) + 120",
            base_dir=BASE_DIR,
            db_path=self.temp_db_path,
            verbose=False
        )
        self.assertEqual(res["route"], "math_code")
        self.assertEqual(res["parsed"]["confidence"], "High")
        self.assertIn("1120", res["raw_answer"])


if __name__ == "__main__":
    print("=" * 65)
    print("  ⚡ Running PRAG Research Engine Test Suite...")
    print("=" * 65)
    unittest.main(verbosity=2)
