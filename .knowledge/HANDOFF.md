# HANDOFF — Agente local para Lucía

## Estado

- Proyecto: `projects/agente-local-amigo/`
- Programa: `agente-local-lucia` (Planner), 7 pasos.
- Pasos 1-5 completados. Paso 6 (eval) en curso. Paso 7 (packaging) pendiente.
- App funcional: `uv run uvicorn src.agent.ui:app --port 8000`.
- Demo: 3 documentos sintéticos, 13 chunks.
- Tests: 8 verdes.

## Qué funciona

- Ingesta de PDFs (texto) y Markdown.
- Chunking por cláusula.
- SQLite + FTS5 + sqlite-vec (`vec0`, `FLOAT[1024]`).
- Embeddings reales con BGE-M3 (`ollama.embed`).
- Retrieval híbrido BM25 + KNN + RRF.
- Agente con `gemma4:12b-mlx` y JSON de salida.
- Verificación determinística de citas (substring exacto).
- UI FastAPI + HTMX: home, ingest, ask, draft, source detail, delete, health.
- Health: 3 docs, 13 chunks, Ollama OK.

## Qué falta

- Probar `gemma4:4b` para latencia (el 12B tarda ~50 s por respuesta en la Mac mini).
- Probar la UI en un navegador real con el flujo completo (drag-and-drop, ask, draft).
- Verificar el botón "Delete everything" en la UI.
- Probar `run.command` en una Mac limpia.

## Fix reciente (2026-11-18)

- **q07 (suma de totales)**: se agregó `src/agent/calc.py` con un cálculo determinístico de `Monto Total` de los contratos. La eval quedó **18/18 (100%)**.
- **Modelos**: `qwen3.5:9b` instalado (7.6 GB). Un prompt simple con `num_ctx=8192` tardó 20.7 s; el RAG completo no mostró mejora clara. `gemma4:12b-mlx` sigue como baseline (~50 s). `num_ctx=8192` hizo más lento a gemma4 (134 s la primera respuesta), así que se revirtió.
- **Tests**: 10 verdes (`test_calc.py` incluido).

## Cómo retomar

1. `cd projects/agente-local-amigo`
2. `uv sync`
3. `uv run python -m src.agent.demo_ingest`
4. `uv run uvicorn src.agent.ui:app --port 8000`
5. Abrir http://127.0.0.1:8000
6. `uv run pytest -q`

## Archivos clave

- `src/agent/db.py` — esquema SQLite + sqlite-vec.
- `src/agent/ingest.py` — extracción + chunking.
- `src/agent/retrieve.py` — BM25 + KNN + RRF.
- `src/agent/agent.py` — LLM + citas.
- `src/agent/verify.py` — substring check.
- `src/agent/ui.py` — FastAPI.
- `ui/mockup.html` — diseño de referencia.
- `eval/questions.yaml` — 18 preguntas.
- `eval/run_eval.py` — runner de la eval.

## Deuda conocida

- `ingest.py` usa `json.dumps(emb)` como string; `sqlite-vec` lo acepta, pero un blob `array('f', emb).tobytes()` sería más eficiente.
- El chunking por headings no detecta cláusulas numeradas sin `#`.
- La UI no usa el mockup completo; es una versión funcional con las mismas clases.
- `test_ui.py::test_delete_ok` borra `data/index.db`; re-ingestar con `make demo` después de correr tests.
