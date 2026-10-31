"""Offline regressions for source parsing, bounded fetches and resumable imports."""
import hashlib
import os
from pathlib import Path
import tempfile
import sqlite3
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import import_security_docs as docs


class SecurityImportTests(unittest.TestCase):
    def test_main_excludes_scripts_navigation_and_footer(self) -> None:
        parser = docs.DocumentParser()
        parser.feed('<nav>menu</nav><main><h1>Guide</h1><script>bad()</script>'
                    '<pre>nmap -sV\nVersion detection</pre></main><footer>noise</footer>')
        self.assertIn('nmap -sV\nVersion detection', parser.text())
        self.assertNotIn('bad()', parser.text())
        self.assertNotIn('noise', parser.text())
        self.assertNotIn('menu', parser.text())

    def test_fetch_enforces_size_limit_and_backs_off(self) -> None:
        too_large = MagicMock()
        too_large.__enter__.return_value = too_large
        too_large.status_code = 200
        too_large.url = 'https://example.org/doc'
        too_large.headers = {'Content-Type': 'text/html'}
        too_large.iter_content.return_value = [b'x' * (docs.MAX_BYTES + 1)]
        session = MagicMock()
        session.get.return_value = too_large
        with patch.object(docs._LOCAL, 'session', session, create=True), \
                patch.dict('sys.modules', {'requests': SimpleNamespace()}), \
                patch.object(docs.time, 'sleep'), patch.object(docs, '_NEXT_REQUEST', 0):
            with self.assertRaisesRegex(ValueError, 'size limit'):
                docs.fetch('https://example.org/doc')
        limited = MagicMock()
        limited.__enter__.return_value = limited
        limited.status_code = 429
        limited.headers = {'Retry-After': '60'}
        good = MagicMock()
        good.__enter__.return_value = good
        good.status_code = 200
        good.url = 'https://example.org/doc'
        good.headers = {'Content-Type': 'text/html'}
        good.encoding = 'utf-8'
        good.iter_content.return_value = [b'<main>Documentation</main>']
        session.get.side_effect = [limited, good]
        with patch.object(docs._LOCAL, 'session', session, create=True), \
                patch.dict('sys.modules', {'requests': SimpleNamespace()}), \
                patch.object(docs.time, 'sleep') as sleep, patch.object(docs, '_NEXT_REQUEST', 0):
            text, _ = docs.fetch('https://example.org/doc')
            self.assertIn('Documentation', text)
            self.assertTrue(any(call.args[0] > 50 for call in sleep.call_args_list))

    def test_index_preserves_provenance_and_skips_unchanged_files(self) -> None:
        class Vector(list):
            def tolist(self) -> list:
                return list(self)

        class Embedder:
            def encode(self, texts: list, **kwargs) -> list:
                self.batch_size = kwargs['batch_size']
                return [Vector([0.1] * 768) for _ in texts]

        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, docs.SUBDIR))
            relative = os.path.join(docs.SUBDIR, 'test.txt')
            raw = ('Document content. ' * 400 + '\n    \n   \n\nFinal content.').encode()
            Path(os.path.join(root, relative)).write_bytes(raw)
            manifest = {'test': {'status': 'downloaded', 'path': relative,
                                 'sha256': hashlib.sha256(raw).hexdigest(),
                                 'resolved_url': 'https://example.org/doc', 'retrieved_at': '2026-10-22'}}
            model = Embedder()
            with patch('embed_store.get_embedder', return_value=model), \
                    patch.dict('sys.modules', {'torch': SimpleNamespace(set_num_threads=lambda _: None)}):
                first = docs.index_documents(root, manifest, logger_func=lambda _: None)
                second = docs.index_documents(root, manifest, logger_func=lambda _: None)
            self.assertEqual(first['indexed'], 1)
            self.assertEqual(second['skipped'], 1)
            self.assertEqual(model.batch_size, 4)
            conn = sqlite3.connect(os.path.join(root, 'data', 'vectors.db'))
            rows = conn.execute('SELECT chunk_text FROM chunks').fetchall()
            conn.close()
            self.assertGreater(len(rows), 1)
            for row in rows:
                self.assertIn('Source URL: https://example.org/doc', row[0])
                self.assertLess(len(row[0]), 2000)
                self.assertNotIn('\n    \n', row[0])

    def test_database_backup_preserves_existing_data(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, 'data'))
            path = os.path.join(root, 'data', 'vectors.db')
            conn = sqlite3.connect(path)
            conn.execute('CREATE TABLE example (value TEXT)')
            conn.execute("INSERT INTO example VALUES ('preserved')")
            conn.commit()
            backup = docs.backup_database(root)
            conn.close()
            copied = sqlite3.connect(backup)
            self.assertEqual(copied.execute('SELECT value FROM example').fetchone()[0], 'preserved')
            copied.close()

    def test_non_https_rejected_without_network(self) -> None:
        with self.assertRaises(ValueError):
            docs.fetch('http://example.org/')

    def test_cache_verification_and_failure_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            with patch.dict(docs.GUIDES, {'test': 'https://example.org/doc'}, clear=True), \
                    patch('sync_kali_docs.CURATED_TOOLS', []), \
                    patch.object(docs.time, 'sleep'), \
                    patch.object(docs, 'fetch', return_value=('<main>' + 'Guide text. ' * 50 + '</main>',
                                                              'https://example.org/doc')) as fetch:
                first = docs.import_documents(root, logger_func=lambda _: None)
                second = docs.import_documents(root, logger_func=lambda _: None)
                self.assertEqual(fetch.call_count, 1)
                path = os.path.join(root, first['test']['path'])
                self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(), second['test']['sha256'])
                with open(path, 'w') as handle:
                    handle.write('modified')
                docs.import_documents(root, logger_func=lambda _: None)
                self.assertEqual(fetch.call_count, 2)
                fetch.side_effect = TimeoutError('offline')
                failed = docs.import_documents(root, refresh=True, logger_func=lambda _: None)
                self.assertEqual(failed['test']['status'], 'failed')
                self.assertTrue(os.path.exists(path))


if __name__ == '__main__':
    unittest.main()
