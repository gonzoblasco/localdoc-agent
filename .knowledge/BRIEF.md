# BRIEF — Agente Local para Lucía

## Objetivo
Construir un agente local, open-source, que le permita a Lucía (fotógrafa freelance) consultar sus contratos y facturas con cita exacta y generar recordatorios de pago en Markdown para Obsidian. Sin deadline de challenge. El éxito es que Lucía lo use y le sirva.

## Persona
- **Nombre:** Lucía (seudónimo)
- **Profesión:** Fotógrafa freelance (bodas y eventos).
- **Tarea recurrente que odia:** Revisar contratos y facturas para saber qué clientes le deben plata, y redactar recordatorios de pago.
- **Dato sensible:** Contratos con datos de clientes, montos, fechas y notas personales.
- **Output esperado:** Un borrador de recordatorio de pago en Markdown, listo para guardar en Obsidian.
- **Hardware:** MacBook (asumido ≥16 GB; verificar).

## Stack (decidido en auditoría 2026-11-18)
- Runtime: Ollama local.
- Modelo: Gemma 4 12B (≥16 GB) / Qwen3.5-9B (8 GB).
- Embeddings: BGE-M3.
- Store: SQLite + sqlite-vec + FTS5.
- Harness: smolagents (Python, Apache 2.0).
- UI: FastAPI + HTMX.
- Packaging: uv + Makefile + run.command.
- Evaluación: 18 preguntas + métricas.
- Licencia: MIT.

## Alcance
- Ingesta de PDFs de contratos y facturas (texto seleccionable).
- Chunking por cláusula/sección.
- RAG híbrido (BM25 + vector + RRF).
- Respuesta con cita exacta (substring check).
- Acción: generar draft de recordatorio de pago en `output/`.
- UI local de una pantalla.
- Privacy proof (0 requests salientes).
- Botón "Delete everything".
- Handover con guía y video.

## Fuera de alcance
- PDFs escaneados / OCR avanzado.
- Notas de voz.
- CSV.
- Docker para Lucía.
- Múltiples usuarios o nube.

## Definition of Done
- [ ] Lucía abre la app en <10 min sin terminal.
- [ ] 10/10 preguntas de muestra devuelven cita válida o refusal correcto.
- [ ] 100% de citas pasan substring check.
- [ ] Query con Wi-Fi apagado no genera requests salientes.
- [ ] "Delete everything" borra índice, embeddings, logs y drafts.
- [ ] Lucía completa la tarea en <5 min y la usaría de nuevo.
- [ ] Repo reproducible con `make demo` y datos sintéticos.

## Preguntas abiertas
1. Confirmar hardware de Lucía.
2. Confirmar formato exacto de los contratos (PDF texto vs. escaneado).
3. Confirmar si usa Obsidian y en qué carpeta.


## Migrado del HANDOFF (projects/localdoc-agent/.knowledge/HANDOFF.md)

Contenido propio del HANDOFF que vivia solo alla. El HANDOFF ahora es
el estado de la ultima sesion (ADR-122).

- Rerun del eval con el 12B cuando esté instalado para medir first-try/retry; bio de GitHub; dev.to API key.
- El chequeo de literales se salta en deterministic_calc y canonicaliza fechas/montos. No se inventó el split de reintentos: el eval ahora lo registra.
