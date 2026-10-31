# PRAG — project brief

**Problem:** answer research questions while retaining the evidence needed to inspect the answer.

**Implementation:** deterministic routing → embedding retrieval → reranking → evidence windows → local generation → citations and metadata.

## Design decisions

| Decision | Reason | Tradeoff |
| :--- | :--- | :--- |
| SQLite-vec | A portable local file without a separate vector-server process | Index size, query cost, and backup behavior still need measurement |
| Rule-based routing | Inspectable decisions without an extra model call | Rules need maintenance for new domains |
| Question-focused excerpts | Preserve relevant text within a bounded prompt | Poor selection can still omit useful context |
| Literal option recovery | Recover a specific tool definition outside semantic top-K | Matching must stay scoped to the named tool |
| Insufficient-evidence response | Make a missing factual basis visible | The broader generation path can still produce errors |
| Shared CLI/web pipeline | Keep evidence and answer behavior aligned | Streaming adds event-order and cancellation concerns |

## Interview walkthrough

1. Ingest the small [original demo document](examples/demo-corpus/overview.md).
2. Ask a question covered by that document.
3. Compare the answer to the excerpt and numbered citation.
4. Ask a question the corpus cannot establish and inspect the evidence behavior.
5. Open `scripts/test_answer_evidence.py` and `scripts/test_retrieve_options.py`.

The demo document contains no personal information and is not a benchmark dataset.

## Verification boundary

The lightweight regression suite checks readiness, evidence windows, literal lookup, and bounded source imports without inference. End-to-end answer quality depends on the selected model, corpus, and cached embedding/reranker models. Use [DEPLOYMENT.md](DEPLOYMENT.md) to rehearse inference separately.
