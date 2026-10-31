# PRAG presentation and local deployment

PRAG remains a local application bound to `127.0.0.1`. The launcher does not
start Ollama, download models, install services or leave a hidden PRAG daemon.

## Preflight

From the project root:

```bash
./launch.sh --check
```

The check reads installed package metadata, opens the corpus read-only and
checks Ollama's installed-model endpoint without loading a model into RAM.
It exits nonzero for missing dependencies, an empty/missing corpus, or an
unavailable/model-less Ollama server. Passing preflight still requires a real
query rehearsal; it does not prove cached embedder/reranker models are usable.

On this workstation on 2026-10-22, dependencies and the database (149 chunks)
pass. After owner authorization, Ollama was started and qwen2.5:3b inference was
verified. The option-definition regression is also verified through the CLI;
this is a focused rehearsal, not a guarantee of every generated answer.

## Interface-only presentation

```bash
./launch.sh --ui-only --no-browser
```

Open `http://127.0.0.1:8000`. This mode skips the Ollama readiness requirement;
it does not fabricate AI answers. Show the interface, indexed sources, status,
history and tool catalog. Querying the LLM still requires Ollama.
Ctrl+C stops the PRAG server. Use `--port 8001` for an occupied port.

## Full local-model rehearsal

After choosing to use the RAM and compute required for inference, start Ollama
in a separate terminal:

```bash
ollama serve
```

Then, from this project:

```bash
./launch.sh --check
venv/bin/python main.py status
venv/bin/python main.py ask "What is nmap?" -v
./launch.sh
```

If no suitable model is installed, choose one and download it explicitly before
the presentation. Qwen3:8B plus CPU embedding and reranking models can consume
substantial memory on a 16 GB laptop; close unnecessary workloads and rehearse
latency. The project keeps Ollama inference models alive for 30 minutes by
existing policy. After finishing, `ollama ps` shows loaded models; an explicit
`ollama stop MODEL_NAME` unloads the selected model. The launcher does not stop
an Ollama daemon or model used by another application.

For an offline presentation, cache the embedder, reranker and reasoning model
beforehand, and use a question covered by the indexed local corpus. Low-confidence
queries may intentionally use the live web fallback; do not describe that path
as offline. Show cited excerpts and an insufficient-evidence response as well
as a successful answer. Avoid displaying private query history or documents in
a public recording.

## Portability and verification

`launch.sh` resolves its own project directory and uses `venv/bin/python`.
A moved/copied virtual environment may need recreation for the target Python
version. `PRAG_PYTHON` can select another installed environment. `PRAG_PORT`
sets the default port; `--port` overrides it. The launcher refuses occupied
ports and opens the browser only after its own server responds.

```bash
bash -n launch.sh
venv/bin/python -m unittest discover -s scripts -p test_check_ready.py -v
venv/bin/python -m pip check
```

Back up `data/`, `knowledge_base/` and `CONTEXT.md` before ingestion or content
changes. No schema migration, ingestion, source sync or model download is part
of the readiness check.

## Memory-aware model selection and evidence lookups

For a 16 GB laptop, explicitly select the installed smaller model for rehearsal:

```bash
./launch.sh --check --model qwen2.5:3b
./launch.sh --model qwen2.5:3b
```

The selection is passed to this process via `RAG_MODEL`; it does not change the
system Ollama configuration. Preflight refuses an explicitly selected model
that is not installed and never downloads it automatically.

Single command-option questions can be answered deterministically from an exact
matching definition in the retrieved documentation, retaining its numbered source
citation. Conflicting definitions go through normal generation instead of being
silently resolved. Other prompts receive query-focused excerpts of at most 500
characters per chunk; this avoids dropping a requested flag buried after a long
header. Empty factual evidence returns `UNKNOWN` in both streaming and CLI modes.
These checks do not guarantee every generated claim is correct; inspect citations.

The lightweight GitHub workflow runs readiness and evidence regressions without
starting Ollama or downloading language/embedding models. The comprehensive local
suite in `scripts/test_suite.py` also exercises cached embeddings and SQLite-vec.
