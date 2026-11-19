# HANDOFF — localdoc-agent (antes agente-local-amigo)

## Estado: MVP cerrado, repo publico

- Repo: https://github.com/gonzoblasco/localdoc-agent (MIT, publico)
- Programa `agente-local-lucia`: 7/7 pasos cerrados. 10 tests verdes.
- Eval 18/18 (P50 49.5 s) con gemma4:12b-mlx; gemma3:4b 4/18 en 6.8 s; qwen3.5:9b no completo.

## Verificado

- Hybrid retrieval real (BM25 + `vec0` KNN + RRF).
- Citas por substring (`verify.py`); q07 resuelto con calculo determinista (`calc.py`).
- Flujo UI completo: ingesta PDF real, consulta con cita, draft, delete (204).

## Deuda abierta

1. ~50 s por respuesta con el 12B: medir en el hardware final.
2. PDFs escaneados fuera de alcance (sin OCR).
3. Eval pequena y auto-escrita: no es un benchmark independiente.

## Como retomar

```bash
cd projects/agente-local-amigo
uv sync
uv run python -m src.agent.demo_ingest
uv run uvicorn src.agent.ui:app --port 8000
```
