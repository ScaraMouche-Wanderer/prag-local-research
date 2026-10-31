"""Readiness checks must be honest and must not create a missing database."""

import io
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from check_ready import check_database, check_ollama


class ReadinessTests(unittest.TestCase):
    def test_missing_database_is_not_created(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "missing.db")
            self.assertFalse(check_database(path)[0])
            self.assertFalse(os.path.exists(path))

    def test_empty_and_populated_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "test.db")
            conn = sqlite3.connect(path)
            try:
                conn.execute("CREATE TABLE chunks (id INTEGER)")
                conn.commit()
                self.assertFalse(check_database(path)[0])
                conn.execute("INSERT INTO chunks VALUES (1)")
                conn.commit()
                self.assertTrue(check_database(path)[0])
            finally:
                conn.close()

    @patch("check_ready.urllib.request.urlopen", side_effect=OSError("unavailable"))
    def test_unreachable_ollama_fails(self, mocked: object) -> None:
        self.assertFalse(check_ollama("http://127.0.0.1:11434")[0])

    def test_ollama_requires_an_installed_model(self) -> None:
        for body, expected in [(b'{"models": []}', False),
                               (b'{"models": [{"name": "qwen3:8b"}]}', True)]:
            with patch("check_ready.urllib.request.urlopen", return_value=io.BytesIO(body)):
                self.assertEqual(check_ollama("http://127.0.0.1:11434")[0], expected)

    def test_explicit_model_must_be_installed(self) -> None:
        with patch.dict(os.environ, {"RAG_MODEL": "missing-model:latest"}):
            with patch("check_ready.urllib.request.urlopen", return_value=io.BytesIO(b'{"models": [{"name": "qwen2.5:3b"}]}')):
                self.assertFalse(check_ollama("http://127.0.0.1:11434")[0])


if __name__ == "__main__":
    unittest.main()
