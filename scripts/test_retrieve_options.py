"""Exercise literal option retrieval with real SQLite-vec and no model downloads."""

import os
import tempfile
import unittest

import sqlite_vec

from embed_store import get_db_connection, init_db
from retrieve import has_exact_option_definition, retrieve_top_k
from router import evaluate_retrieval_confidence


class QueryVector:
    def tolist(self) -> list[float]:
        return [0.0] * 768


class Embedder:
    def encode(self, *args: object, **kwargs: object) -> QueryVector:
        return QueryVector()


class Reranker:
    def predict(self, pairs: list, **kwargs: object) -> list[float]:
        return [-10.0 if "-sV:" in text else 10.0 for _, text in pairs]


class OptionRetrievalTests(unittest.TestCase):
    def test_named_tool_and_option_case_are_required(self) -> None:
        self.assertTrue(has_exact_option_definition("Explain nmap -sV", "-sV: Version detection", "/docs/nmap.txt"))
        self.assertFalse(has_exact_option_definition("Explain nmap -sv", "-sV: Version detection", "/docs/nmap.txt"))
        self.assertFalse(has_exact_option_definition("Explain curl -sV", "-sV: Version detection", "/docs/nmap.txt"))

    def test_definition_outside_semantic_top_k_remains_local(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "vectors.db")
            init_db(path)
            conn = get_db_connection(path)
            try:
                for index in range(11):
                    text = "General Nmap introduction" if index < 10 else "-sV: Probe open ports to determine service/version info"
                    cursor = conn.execute(
                        "INSERT INTO chunks(file_path, file_type, page_number, chunk_index, chunk_text, source_type) VALUES(?, ?, ?, ?, ?, ?)",
                        ("/docs/nmap.txt", "txt", 1, index, text, "kali_docs")
                    )
                    vector = [0.0] * 768 if index < 10 else [10.0] * 768
                    conn.execute("INSERT INTO chunk_vectors(rowid, embedding) VALUES (?, ?)",
                                 (cursor.lastrowid, sqlite_vec.serialize_float32(vector)))
                conn.commit()
            finally:
                conn.close()
            chunks = retrieve_top_k("What does nmap -sV do?", folder, path, top_k=1,
                                    source_type="kali_docs", embedder=Embedder(), reranker=Reranker())
            self.assertEqual(len(chunks), 1)
            self.assertIn("-sV:", chunks[0]["chunk_text"])
            self.assertLess(chunks[0]["rerank_score"], 0.01)
            confidence = evaluate_retrieval_confidence(chunks, route="kali_docs", question="What does nmap -sV do?")
            self.assertFalse(confidence["route_to_web_fallback"])
            self.assertTrue(confidence["exact_option_match"])


if __name__ == "__main__":
    unittest.main()
