# localdoc-agent — verifiable citations, entirely on your laptop

A local-first AI agent that answers questions about contracts and invoices, with **citations that are verified in code**, not trusted from the model.

Every answer carries a `chunk_id` and a literal quote. The app checks that the quote is a substring of the retrieved chunk. If it is not, the answer is refused. No network, no API key, no hallucinated page numbers.

> **Origin:** built as a design exercise for the [DEV.to Hacktoberfest 2026 — Weekend Challenge: Build for a Friend](https://dev.to/challenges/hacktoberfest-weekend-2026-10-01). The challenge asked for something that solves a real problem for one specific person, built with open-source AI.
>
> The official window closed on **October 5, 2026**; this build started afterwards, so it is **not a submission**. The case study (“Lucía, a freelance photographer”) is a *persona*, not a real person — it exists to give the design a concrete constraint, not to claim a testimonial.

---

## The idea

Ask a question about a folder of contracts. Get:

- an answer;
- the exact clause it came from;
- the document and page;
- a refusal when the evidence is not there.

The hard part is not retrieval. The hard part is **not lying**.

## How the citations stay honest

```python
valid, invalid = verify_citations(citations, chunks_by_id)
```

A citation is valid only if its `quote` is a substring of the chunk after normalization. The normalizer handles whitespace, NFKC ligatures (`fi`), smart quotes, soft hyphens, NBSP and words hyphenated across a line break. If the model invents a quote, it fails, the model is asked once more, and if it fails again the response becomes a refusal.

The quote check alone proves the text exists. It does not prove the text supports the answer. A second deterministic check extracts dates, amounts, percentages and clause numbers from the answer and requires each one to appear in at least one valid quote. Values produced by the deterministic calculator are exempt, because a sum of two cited totals does not appear literally in either one.

This is not another LLM checking the first one. It is string containment, and it can be reproduced by anyone with the database.

## What it runs on

| Layer | Choice | Why |
|---|---|---|
| Runtime | Ollama | Local inference, OpenAI-compatible API |
| Model | `gemma4:12b-mlx` (7.7 GB) | 18/18 on the eval; the smaller models were not accurate enough (see below) |
| Embeddings | `bge-m3` (1024d) | Multilingual; the documents are in Spanish |
| Store | SQLite + FTS5 + `sqlite-vec` (`vec0`) | One file; hybrid search; metadata for citations |
| Retrieval | BM25 + KNN + RRF | Handles both concepts (“saldo pendiente”) and exact strings (“$15.000,00”) |
| LLM API | `ollama.embed` / `ollama.chat` | The CLI has no `embed` subcommand — a real bug found during the build |
| Verification | Substring containment | Deterministic; no second model |
| Arithmetic | `calc.py` (deterministic) | Because a 12B model cannot add two numbers reliably |
| UI | FastAPI + HTMX | One screen, no build step |

## Local or cloud

The default is local: `gemma4:12b-mlx`, no network, no account.

The UI also offers `gemma4:cloud`, which runs on Ollama Cloud and requires an explicit consent checkbox. With a cloud model, the question and the retrieved chunks leave the machine; the zero-sockets claim only applies to the local mode.

Ollama's published prices (2026-11-19, per 1M tokens):

| Model | Input | Cached input | Output |
|---|---:|---:|---:|
| `gemma4:cloud` | $0.14 | $0.05 | $0.40 |
| `deepseek-v4.1-flash:cloud` | $0.30 peak / $0.15 off-peak | $0.006 / $0.003 | $1.20 / $0.60 |

`deepseek-v4.1-flash` is a 763B model and costs roughly twice as much on input and three times as much on output. It stays available in the selector for the cases where the smaller cloud model is not enough.

## The privacy claim is tested, not asserted

"Nothing leaves this machine" used to be demonstrated once, with `lsof` and the Wi-Fi off. That is an experiment, not a guarantee: it proves what happened at 3pm on one laptop.

It is now four checks in `tests/test_privacy.py`:

1. **A socket audit hook.** `tests/privacy_probe.py` runs the real code paths in a subprocess under `sys.addaudithook` and records every `socket.connect`, `socket.getaddrinfo` and `socket.gethostbyname` whose target is not loopback. DNS counts: resolving a name is already traffic.
2. **A positive control.** `test_probe_detects_a_simulated_leak` deliberately connects to `example.com` and fails if the hook does *not* catch it. Without this, a broken hook would pass every other test in the file while certifying nothing.
3. **A bind guard.** `make run` goes through `src/agent/serve.py`, which refuses `--host 0.0.0.0` with exit code 2 instead of quietly accepting a copy-pasted command line.
4. **A delete that deletes.** `POST /delete` removes the database, its `-wal`/`-shm` sidecars, `output/`, and — the real leak — the uploaded originals in `data/private/`.

Run only these: `uv run pytest -q tests/test_privacy.py`

**What it does not cover, stated plainly.** The hook lives inside the Python process. A subprocess is invisible to it, and so is the Ollama daemon: when a requested model is not downloaded, *Ollama* fetches it from the registry, outside anything Python can audit. That is why local models are a Quickstart prerequisite instead of a first-run download, and why cloud mode requires explicit consent.

## Quickstart

```bash
# 1. Models
ollama pull gemma4:12b-mlx
ollama pull bge-m3

# 2. Install and index the demo corpus
uv sync
uv run python -m src.agent.demo_ingest     # 3 documents, 13 chunks

# 3. Run
uv run uvicorn src.agent.ui:app --port 8000
# open http://127.0.0.1:8000

# 4. Tests
uv run pytest -q                            # 10 tests
```

The UI supports drag-and-drop ingestion, chat with citations, a sources panel, a Markdown draft for an invoice reminder, and a **Delete everything** button.

## The eval (18 questions)

| Model | Accuracy | P50 latency | Notes |
|---|---:|---:|---|
| `gemma4:12b-mlx` | **18/18 (100 %)** | 49.5 s | Chosen |
| `gemma3:4b` | 4/18 (22 %) | 6.8 s | Fast, wrong on dates and amounts |
| `qwen3.5:9b` | did not complete | >90 s | Context 262k kept the model resident; not viable here |

Questions are split into easy, multi-hop, no-answer, and numeric. The scorer is in `eval/rescore.py`; raw results are in `eval/results.json`.

**The 18/18 is not purely the model.** Question 7 (sum of two contract totals) is answered by a deterministic calculator (`src/agent/calc.py`) because a 12B model does not do arithmetic reliably. That is the design: the LLM retrieves and composes; code does the math.

## What went wrong (and what changed because of it)

This section exists because the first version was not good, and the failures are the most useful part of the repository.

1. **Mock embeddings passed the tests.** The first implementation called `ollama embed` as a CLI command, which does not exist. Every embedding silently fell back to a 3-dimension mock vector, and the tests were green. Fixed by using the Python API (`ollama.embed`, 1024 dims) and removing the silent fallback: if embeddings fail, the ingest fails loudly.
2. **`sqlite-vec` was never actually loaded.** `chunks_vec` was quietly created as a regular table, so vector search ran on a brute-force path that returned garbage. Fixed by calling `sqlite_vec.load(conn)` behind `enable_load_extension(True)` and asserting the schema is a `vec0` virtual table.
3. **Subagents reported files they never wrote.** Three times a delegate claimed to have created a module that did not exist on disk. The fix was procedural: every report is verified against the filesystem and the test suite before it is accepted.
4. **A 4B model is not a small version of a 12B model.** It is 4.5× less accurate on this task. The speed/accuracy trade-off was measured, not assumed, and the data is in the repo.
5. **A 9B model can be slower than a 12B one.** `qwen3.5:9b` stayed resident with a 262k context and took over 90 s per answer. Bigger is not always slower; context settings matter more than parameter count.
6. **A 12B model will confidently answer a sum wrong.** Hence the calculator.
7. **FTS5 treats a question mark as syntax.** Natural questions crashed the retriever until the query was tokenized and rebuilt.

## Limitations

- **PDFs must have selectable text.** Scanned documents are rejected with an explicit message; OCR is out of scope.
- **One language per corpus.** The embeddings are multilingual, but the prompt and the demo are in Spanish.
- **~50 s per answer** on an Apple Silicon Mac mini with a 12B model. Correct, not fast.
- **The eval is small and authored by the same person who wrote the system.** It is honest about the 18 questions it asks, not a benchmark.
- **No multi-user, no server, no sync.** It is a local tool.
- **The privacy test cannot see subprocesses.** It audits Python sockets; the Ollama daemon pulling a missing model happens in another process. The test proves the app's own code stays on loopback, not that every dependency behaves.

## Repository layout

```
src/agent/
  db.py          SQLite schema, FTS5, sqlite-vec
  ingest.py      PDF/Markdown extraction + clause chunking
  retrieve.py    BM25 + KNN + RRF hybrid search
  agent.py       LLM call, JSON contract, retry on invalid citations
  verify.py      deterministic substring verification
  calc.py        deterministic arithmetic for contract totals
  ui.py          FastAPI routes
eval/
  questions.yaml 18 questions
  run_eval.py    runner with latency
  rescore.py     tolerant re-scoring (documented)
docs/
  ARCHITECTURE.md  schema, chunking, retrieval, security
  decisions.md     ADR-001 to ADR-007
```

## Origin and credits

- **Challenge:** [DEV.to Hacktoberfest 2026, Weekend Challenge — Build for a Friend](https://dev.to/challenges/hacktoberfest-weekend-2026-10-01).
- **Design context:** a full audit of the original plan, including the eligibility gate (the challenge had closed) and the decision to pivot from a submission to a public project (`docs/` in the author's workspace; summarized here).
- **Models:** [Gemma 4](https://ai.google.dev/gemma) and [BGE-M3](https://huggingface.co/BAAI/bge-m3). Model weights keep their own licences.

## License

MIT — see `LICENSE`. Model weights keep their own licences.
