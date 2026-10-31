#!/usr/bin/env python3
"""Explicit, resumable primary-source imports; independent of ephemeral web fallback."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import threading
from urllib.parse import urljoin, urlparse

_LOCAL = threading.local()
_RATE_LOCK = threading.Lock()
_NEXT_REQUEST = 0.0
MAX_BYTES = 3_000_000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBDIR = os.path.join('knowledge_base', 'Documentation', 'Security')
GUIDES = {
    'kali-catalogue': 'https://www.kali.org/tools/all-tools/',
    'owasp-wstg': 'https://wstg.owasp.org/v4.2/',
    'owasp-testing-framework': 'https://wstg.owasp.org/v4.2/3-The_OWASP_Testing_Framework/',
    'owasp-testing': 'https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/',
    'owasp-sql-injection': ('https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/'
                            '07-Input_Validation_Testing/05-Testing_for_SQL_Injection'),
    'owasp-reflected-xss': ('https://wstg.owasp.org/v4.2/4-Web_Application_Security_Testing/'
                            '07-Input_Validation_Testing/01-Testing_for_Reflected_Cross_Site_Scripting'),
    'owasp-top-ten': 'https://owasp.org/www-project-top-ten/',
    'mitre-attack': 'https://attack.mitre.org/techniques/T1190/',
    'tor-onion-overview': 'https://community.torproject.org/onion-services/overview/',
    'tor-onion-security': 'https://community.torproject.org/onion-services/advanced/opsec/',
    'tor-specification': 'https://spec.torproject.org/intro/index.html',
    'nmap-reference': 'https://nmap.org/book/man.html',
    'zap-getting-started': 'https://www.zaproxy.org/getting-started/',
    'portswigger-testing': 'https://portswigger.net/web-security',
}


class DocumentParser(HTMLParser):
    """Extract readable main content without scripts, menus or executable markup."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.links = []
        self.skip = 0
        self.main = False
        self.main_parts = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attrs = dict(attrs)
        if tag in ('script', 'style', 'nav', 'footer', 'header'):
            self.skip += 1
        if tag == 'main':
            self.main = True
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
        if tag in ('p', 'div', 'br', 'li', 'pre', 'h1', 'h2', 'h3', 'tr'):
            self.handle_data('\n')

    def handle_endtag(self, tag: str) -> None:
        if tag in ('script', 'style', 'nav', 'footer', 'header'):
            self.skip = max(0, self.skip - 1)
        if tag == 'main':
            self.main = False
        if tag in ('p', 'div', 'li', 'pre', 'h1', 'h2', 'h3', 'tr'):
            self.handle_data('\n')

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)
            if self.main:
                self.main_parts.append(data)

    def text(self) -> str:
        text = ''.join(self.main_parts or self.parts)
        return re.sub(r'\n[ \t]*\n+', '\n\n', text).strip()


def fetch(url: str) -> tuple[str, str]:
    if urlparse(url).scheme != 'https':
        raise ValueError('Only HTTPS documentation sources are supported')
    import requests
    if not hasattr(_LOCAL, 'session'):
        _LOCAL.session = requests.Session()
        _LOCAL.session.headers['User-Agent'] = 'PRAG-DocumentationImporter/1.0 (personal offline research)'
    global _NEXT_REQUEST
    for attempt in range(4):
        # One global request per second, also across download workers.
        with _RATE_LOCK:
            delay = max(0, _NEXT_REQUEST - time.monotonic())
            _NEXT_REQUEST = max(_NEXT_REQUEST, time.monotonic()) + 1.0
        if delay:
            time.sleep(delay)
        with _LOCAL.session.get(url, stream=True, timeout=30) as response:
            if response.status_code in (429, 503) and attempt < 3:
                value = response.headers.get('Retry-After', '')
                wait = min(300, max(30 * (attempt + 1), int(value) if value.isdigit() else 60))
                with _RATE_LOCK:
                    _NEXT_REQUEST = max(_NEXT_REQUEST, time.monotonic() + wait)
                continue
            response.raise_for_status()
            if urlparse(response.url).scheme != 'https':
                raise ValueError('Insecure redirect rejected')
            if 'text/html' not in response.headers.get('Content-Type', ''):
                raise ValueError('Expected an HTML documentation page')
            raw = bytearray()
            for block in response.iter_content(chunk_size=65536):
                raw.extend(block)
                if len(raw) > MAX_BYTES:
                    raise ValueError('Document exceeds size limit')
            return raw.decode(response.encoding or 'utf-8', errors='replace'), response.url
    raise RuntimeError('Documentation source remained unavailable')



def atomic_write(path: str, text: str) -> None:
    with open(path + '.tmp', 'w', encoding='utf-8') as handle:
        handle.write(text)
    os.replace(path + '.tmp', path)


def backup_database(base_dir: str) -> str | None:
    path = os.path.join(base_dir, 'data', 'vectors.db')
    if not os.path.exists(path):
        return None
    backup = path + '.before-security-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f') + '.bak'
    source = sqlite3.connect(path)
    target = sqlite3.connect(backup)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()
    return backup


def import_documents(base_dir: str, all_kali: bool = False, refresh: bool = False,
                     logger_func=print) -> dict:
    from sync_kali_docs import CURATED_TOOLS
    directory = os.path.join(base_dir, SUBDIR)
    os.makedirs(directory, exist_ok=True)
    manifest_path = os.path.join(base_dir, 'data', 'security-docs-manifest.json')
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8')) if os.path.exists(manifest_path) else {}
    sources = dict(GUIDES)
    aliases = {'burp': 'burpsuite', 'zap': 'zaproxy', 'metasploit': 'metasploit-framework',
               'msfconsole': 'metasploit-framework', 'searchsploit': 'exploitdb',
               'airmon-ng': 'aircrack-ng', 'aireplay-ng': 'aircrack-ng',
               'airodump-ng': 'aircrack-ng', 'airbase-ng': 'aircrack-ng'}
    tools = {aliases.get(tool, tool) for tool in CURATED_TOOLS}
    if all_kali:
        html, _ = fetch(GUIDES['kali-catalogue'])
        parser = DocumentParser()
        parser.feed(html)
        tools.update(match.group(1) for link in parser.links
                     if (match := re.fullmatch(r'/tools/([a-z0-9+.-]+)/',
                                              urlparse(urljoin(GUIDES['kali-catalogue'], link)).path))
                     and match.group(1) != 'all-tools')
    sources.update({f'kali-{tool}': f'https://www.kali.org/tools/{tool}/' for tool in sorted(tools)})
    def download(name: str, url: str) -> tuple[str, dict]:
        path = os.path.join(directory, name + '.txt')
        old = manifest.get(name, {})
        if not refresh and old.get('status') == 'downloaded' and old.get('url') == url and os.path.exists(path):
            digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            if digest == old.get('sha256'):
                logger_func(f'[CACHED] {name}')
                return name, old
        try:
            html, resolved = fetch(url)
            parser = DocumentParser()
            parser.feed(html)
            text = parser.text()
            if len(text) < 200:
                raise ValueError('No substantial documentation text')
            stamp = datetime.now(timezone.utc).isoformat()
            document = (f'{name}\nSource URL: {resolved}\nRetrieved: {stamp}\n'
                        f'Publisher retains copyright; local research copy.\n\n{text}\n')
            atomic_write(path, document)
            result = {'url': url, 'resolved_url': resolved, 'retrieved_at': stamp,
                              'status': 'downloaded', 'characters': len(text),
                              'sha256': hashlib.sha256(document.encode()).hexdigest(),
                              'path': os.path.relpath(path, base_dir)}
            logger_func(f'[SAVED] {name}: {len(text)} characters')
        except Exception as error:
            result = {**old, 'url': url, 'status': 'failed', 'error': str(error)}
            logger_func(f'[FAILED] {name}: {error}')
        time.sleep(0.4)
        return name, result
    logger_func(f'Planned sources: {len(sources)} (Kali package pages plus public guides)')
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(download, name, url) for name, url in sources.items()]
        for future in as_completed(futures):
            name, result = future.result()
            manifest[name] = result
            atomic_write(manifest_path, json.dumps(manifest, indent=2) + '\n')
    for alias, package in aliases.items():
        key = f'kali-{alias}'
        if key in manifest and manifest.get(f'kali-{package}', {}).get('status') == 'downloaded':
            manifest[key] = {'status': 'covered_by_package', 'package': f'kali-{package}'}
    atomic_write(manifest_path, json.dumps(manifest, indent=2) + '\n')
    return manifest


def index_documents(base_dir: str, manifest: dict, logger_func=print) -> dict:
    """Index verified downloads with provenance in every bounded evidence chunk."""
    from embed_store import get_embedder, get_stored_file_hash, init_db, store_chunks_and_embeddings
    db_path = os.path.join(base_dir, 'data', 'vectors.db')
    logger_func(f'Database backup: {backup_database(base_dir)}')
    init_db(db_path)
    embedder = None
    counts = {'indexed': 0, 'skipped': 0, 'failed': 0, 'chunks': 0}
    for name, item in manifest.items():
        if item.get('status') != 'downloaded':
            continue
        try:
            path = os.path.join(base_dir, item['path'])
            raw = Path(path).read_bytes()
            if hashlib.sha256(raw).hexdigest() != item['sha256']:
                raise ValueError('Downloaded file hash differs from manifest; refresh it first')
            # Version the indexing recipe so changes are not silently skipped.
            digest = hashlib.sha256(b'provenance-chunks-v2\0' + raw).hexdigest()
            if get_stored_file_hash(db_path, item['path']) == digest:
                counts['skipped'] += 1
                continue
            text = raw.decode('utf-8')
            # HTML template whitespace is not useful retrieval evidence. Preserve code indentation.
            text = '\n'.join(line.rstrip() for line in text.splitlines())
            text = re.sub(r'\n{3,}', '\n\n', text).strip()
            if text.startswith(name + '\nSource URL:') and '\n\n' in text:
                text = text.split('\n\n', 1)[1]
            prefix = f"{name}\nSource URL: {item['resolved_url']}\nRetrieved: {item['retrieved_at']}\n\n"
            chunks = []
            while text:
                end = min(1800, len(text))
                if end < len(text):
                    boundary = text.rfind('\n', 900, end)
                    if boundary > 0:
                        end = boundary + 1
                chunks.append({'file_type': 'txt', 'page_number': 1, 'chunk_index': len(chunks),
                               'chunk_text': prefix + text[:end]})
                text = text[end:]
            if embedder is None:
                import torch
                torch.set_num_threads(2)
                model = get_embedder()

                class SmallBatchEmbedder:
                    def encode(self, texts: list, **kwargs) -> object:
                        return model.encode(texts, batch_size=4, **kwargs)

                embedder = SmallBatchEmbedder()
            inserted = store_chunks_and_embeddings(db_path, item['path'], digest, chunks, embedder,
                                                   source_type='kali_docs')
            counts['indexed'] += 1
            counts['chunks'] += inserted
            logger_func(f'[INDEXED] {name}: {inserted} chunks')
        except Exception as error:
            counts['failed'] += 1
            logger_func(f'[INDEX FAILED] {name}: {error}')
    atomic_write(os.path.join(base_dir, 'data', 'security-index-report.json'),
                 json.dumps({**counts, 'finished_at': datetime.now(timezone.utc).isoformat()}, indent=2) + '\n')
    logger_func(str(counts))
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all-kali', action='store_true',
                        help='Enumerate all package pages linked by the Kali catalogue')
    parser.add_argument('--refresh', action='store_true', help='Refetch previously downloaded documents')
    parser.add_argument('--ingest', action='store_true', help='Back up SQLite and index the downloaded documents')
    args = parser.parse_args()
    manifest = import_documents(ROOT, args.all_kali, args.refresh)
    print(f"Downloaded: {sum(item.get('status') == 'downloaded' for item in manifest.values())}; "
          f"failed: {sum(item.get('status') == 'failed' for item in manifest.values())}")
    if args.ingest:
        result = index_documents(ROOT, manifest)
        if result['failed']:
            raise SystemExit(1)


if __name__ == '__main__':
    main()
