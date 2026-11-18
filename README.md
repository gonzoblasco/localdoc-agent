# Nido — Agente local para Lucía

Nido es un agente local y privado que responde preguntas sobre los contratos y facturas de Lucía, con cita exacta del documento. Corre 100 % en su Mac: no manda datos a ninguna nube.

## Qué hace

- Ingesta PDFs (con texto seleccionable) y Markdown.
- Chunking por cláusula, con metadata de documento, página y sección.
- Búsqueda híbrida BM25 + vectores (BGE-M3) + RRF.
- Respuesta con citas verificables (substring exacto).
- Genera recordatorios de pago en Markdown para Obsidian.
- Botón "Delete everything" que borra índice, embeddings, logs y borradores.

## Requisitos

- macOS con Apple Silicon.
- [Ollama](https://ollama.com/) instalado y corriendo.
- `uv` (`brew install uv`).
- Modelos:

```bash
ollama pull gemma4:12b-mlx
ollama pull bge-m3
```

## Instalación

```bash
cd agente-local-amigo
uv sync
```

## Uso

Doble clic en `run.command` o:

```bash
make run
```

Abrí http://127.0.0.1:8000.

## Demo con datos sintéticos

```bash
make demo
```

Esto ingesta `data/demo/` y corre una búsqueda de ejemplo.

## Arquitectura

```
[PDFs/Markdown] -> [Ingesta] -> [Chunks por cláusula]
    -> [SQLite: FTS5 + sqlite-vec]
    -> [Retrieval híbrido: BM25 + vector + RRF]
    -> [Agente: Ollama + Gemma 4 12B] -> [JSON con citas]
    -> [Verificación substring] -> [UI FastAPI + HTMX]
    -> [Borrador Markdown]
```

Decisiones: `docs/decisions.md`. Arquitectura detallada: `docs/ARCHITECTURE.md`.

## Privacidad

- No hay requests salientes en el camino crítico.
- El modelo y los embeddings corren locales.
- `data/private/` está en `.gitignore`.
- "Delete everything" borra `data/index.db` y `output/`.

## Limitaciones

- PDFs escaneados (sin texto seleccionable): fuera de alcance. La app avisa.
- Modelo local: ~30-60 s por respuesta en Mac mini con `gemma4:12b-mlx`. Para una laptop más chica, usar `qwen3.5:9b` o `gemma4:4b`.
- Una sola usuaria, un solo corpus.

## Handoff para Lucía

1. Abrí `run.command` (doble clic).
2. Esperá que el navegador abra `http://127.0.0.1:8000`.
3. Arrastrá tus contratos y facturas a la zona de documentos.
4. Preguntá: "¿Qué clientes me deben plata?".
5. Si querés un recordatorio, pedilo y guardalo en Obsidian.
6. Para borrar todo, usá "Delete everything".

Si algo falla, revisá que Ollama esté abierto y que los modelos estén descargados.
