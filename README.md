# PRAG
### Local research with a traceable evidence trail

PRAG is a local-first retrieval-augmented research engine. It searches a local document corpus, reranks evidence, and uses an Ollama model to produce cited answers. Exact command-option definitions can be returned directly from matching evidence; empty factual evidence returns `UNKNOWN`.

**Python · Ollama · SQLite-vec · sentence-transformers · CLI + streaming web interface**

[Project brief](PROJECT_BRIEF.md) · [Presentation](DEPLOYMENT.md) · [Contributing](CONTRIBUTING.md)

## Why build it?

A useful research tool should make its evidence visible. PRAG exposes retrieved excerpts, source tiers, and the route used for a question so an answer can be checked against its inputs.

## How it works

1. A deterministic router classifies the question.
2. SQLite-vec retrieves candidate document chunks.
3. A CrossEncoder reranks semantic matches; literal named-tool option lookup preserves matching definitions outside semantic top-K.
4. The pipeline selects question-focused evidence windows.
5. An Ollama model generates the answer, or a deterministic path returns an exact definition.
6. The CLI and web interface expose citations and response metadata.

Low-confidence questions may use a live web fallback. Local inference does not imply that every query is offline.

## Quick start

Use Python 3.10+ and an Ollama installation. Model installation and the initial embedding/reranker download require network access.

```bash
python3 -m venv venv
source venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

In a separate terminal:

```bash
ollama serve
ollama pull qwen3:8b
```

Create a demonstration corpus from the included original sample document:

```bash
mkdir -p knowledge_base/Notes
cp examples/demo-corpus/*.md knowledge_base/Notes/
python main.py ingest
./launch.sh --check --model qwen3:8b
./launch.sh --model qwen3:8b
```

Open `http://127.0.0.1:8000`. For the interface without inference, use `./launch.sh --ui-only --no-browser`. This mode does not fabricate answers.

## Useful commands

```bash
python main.py status
python main.py sources
python main.py ask "What does the demo component do?" -v
python main.py ask "What information is absent from the demo document?" --json
python main.py sync-kali
```

`sync-kali` builds a local documentation corpus on the current machine. Personal files, generated indexes, history, and imported documentation are not bundled in this source release.

## Offline regression checks

The regression checks below require the lightweight Python clients used by the tests, but do not start a model daemon or download model weights:

```bash
bash -n launch.sh
python -m unittest discover -s scripts -p test_check_ready.py -v
python -m unittest discover -s scripts -p test_answer_evidence.py -v
python -m unittest discover -s scripts -p test_retrieve_options.py -v
python -m unittest discover -s scripts -p test_import_security_docs.py -v
```

See [.github/workflows/checks.yml](.github/workflows/checks.yml) for the CI setup.

## Source map

| Path | Responsibility |
| :--- | :--- |
| `main.py` | CLI and server entry points |
| `scripts/pipeline.py` | Shared question pipeline |
| `scripts/router.py` | Deterministic routing |
| `scripts/retrieve.py` | Semantic retrieval and literal option recovery |
| `scripts/answer.py` | Evidence selection and generation |
| `scripts/embed_store.py` | SQLite-vec storage and model loading |
| `scripts/web_ui.py` | Embedded web interface and streaming endpoints |
| `scripts/import_security_docs.py` | Explicit source import with provenance and bounded downloads |

## Data and limitations

The server is a local application and should remain on loopback. The repository omits personal corpora, vector databases, preferences, and query history. Generated answers still need source review; source-tier labels and scores are retrieval signals, not calibrated correctness guarantees.

