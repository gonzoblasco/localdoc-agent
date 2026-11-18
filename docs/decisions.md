# Decisiones de arquitectura — Agente local para Lucía

## ADR-001: SQLite + sqlite-vec + FTS5 en lugar de Chroma/FAISS

**Contexto:** El agente necesita almacenar chunks, embeddings y metadata para citas exactas. El corpus es pequeño (<50k chunks).

**Decisión:** Usar SQLite con `sqlite-vec` para vectores y FTS5 para BM25. Un solo archivo `data/index.db`.

**Consecuencias:**
- Menos piezas que mantener.
- Metadata relacional para citas (documento, página, cláusula).
- Borrado y backup triviales (un archivo).
- Híbrido BM25 + vector + RRF en una sola query.
- No hay servidor ni telemetría.

## ADR-002: Gemma 4 12B como modelo por defecto

**Contexto:** El modelo debe correr en la MacBook de Lucía (asumido ≥16 GB) y hacer tool calling confiable.

**Decisión:** `gemma4:12b-mlx` (7.7 GB, ya instalado localmente). Fallback: Qwen3.5-9B si el hardware es de 8 GB.

**Consecuencias:**
- Califica para *Best Use of Gemma* (si se publica el caso).
- Tool calling aceptable (33/45 en benchmark de Larsen, oct 2026).
- Si la latencia es alta, bajar a Qwen3.5-9B.

## ADR-003: smolagents como harness

**Contexto:** Ollama es un runtime de inferencia, no un agent harness. El challenge (y la buena práctica) pide un harness open-source.

**Decisión:** `smolagents` (Python, Apache 2.0).

**Consecuencias:**
- Loop de tool calling explícito y auditable.
- Fácil de testear y de mostrar el trace.
- Menos dependencias que Mastra (TS) para un equipo Python.

## ADR-004: FastAPI + HTMX para la UI

**Contexto:** La usuaria final no es técnica. Un CLI no sirve.

**Decisión:** FastAPI + Jinja2 + HTMX. Una sola pantalla: drag-and-drop, chat, panel de fuentes, panel de draft, badge local, botón delete.

**Consecuencias:**
- Sin build de frontend.
- Control visual total.
- Gradio queda como fallback si el tiempo aprieta.

## ADR-005: Sin Docker para la usuaria final

**Contexto:** Docker Desktop no es zero-config para una persona no técnica.

**Decisión:** `uv` + Makefile + `run.command` (macOS). Docker solo para desarrollo.

**Consecuencias:**
- Doble clic para abrir la app.
- Sin daemon ni 1 GB de imágenes.
- Hay que probar en la máquina de Lucía.

## ADR-006: BGE-M3 para embeddings

**Contexto:** Los documentos están en español. `qwen3-embedding:0.6b` está instalado pero es English-centric.

**Decisión:** Usar BGE-M3 (multilingüe, 8k). Descargarlo con `ollama pull bge-m3`.

**Consecuencias:**
- Mejor recall en español.
- Menos citas vacías.
- Verificar licencia y tamaño antes de empaquetar.

## ADR-007: Verificación determinística de citas

**Contexto:** Los LLMs inventan números de página y citas.

**Decisión:** El agente devuelve JSON con `chunk_id`, `page`, `quote`. La app verifica que `quote` sea un substring exacto del chunk. Si falla, reintenta una vez o se niega a responder.

**Consecuencias:**
- La cita es una garantía reproducible, no una promesa.
- El juez (o Lucía) puede verificar.
- Si la tasa de citas válidas no es 100%, no se publica el claim de "exact citations".
