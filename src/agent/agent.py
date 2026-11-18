"""Agente de respuesta con citas verificables."""

from __future__ import annotations

import json
from typing import Any, Dict, List

import ollama

from .retrieve import hybrid_search
from .verify import verify_citations

MODEL = "gemma4:12b-mlx"

_SYSTEM = (
    "Sos un asistente que responde preguntas sobre contratos y facturas. "
    "Respondé en español rioplatense, con tono claro y directo. "
    "Usá solo la información de los fragmentos provistos. "
    "Si no hay evidencia suficiente, decí que no lo encontrás en los documentos. "
    "Devolvé JSON con: answer (string), citations (lista de {chunk_id, quote}), confidence (0-1). "
    "Cada quote debe ser una copia textual exacta del fragmento citado."
)


def _context(chunks: List[Dict[str, Any]]) -> str:
    parts = []
    for c in chunks:
        parts.append(
            f'<chunk id="{c["chunk_id"]}" document="{c.get("document", "")}" '
            f'page="{c.get("page", "")}" section="{c.get("section", "")}">\n'
            f'{c["text"]}\n</chunk>'
        )
    return "\n\n".join(parts)


def answer_question(conn, query: str) -> Dict[str, Any]:
    chunks = hybrid_search(conn, query, top_k=8)
    if not chunks:
        return {
            "answer": "No encontré información sobre eso en tus documentos.",
            "citations": [],
            "sources": [],
            "confidence": 0.0,
        }

    context = _context(chunks)
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": f"Fragmentos:\n{context}\n\nPregunta: {query}"},
    ]

    def call() -> Dict[str, Any]:
        resp = ollama.chat(model=MODEL, messages=messages, format="json")
        content = resp["message"]["content"]
        return json.loads(content)

    chunks_by_id = {c["chunk_id"]: c["text"] for c in chunks}

    try:
        payload = call()
    except Exception as exc:
        raise RuntimeError(f"No se pudo consultar a Ollama: {exc}") from exc

    answer = payload.get("answer", "")
    citations = payload.get("citations", [])
    confidence = float(payload.get("confidence", 0.0))
    valid, invalid = verify_citations(citations, chunks_by_id)

    if invalid:
        try:
            payload = call()
            answer = payload.get("answer", "")
            citations = payload.get("citations", [])
            confidence = float(payload.get("confidence", 0.0))
            valid, invalid = verify_citations(citations, chunks_by_id)
        except Exception:
            pass

    if invalid:
        return {
            "answer": "No pude verificar las citas de esa respuesta. Probá reformular la pregunta.",
            "citations": [],
            "sources": [],
            "confidence": 0.0,
        }

    by_id = {c["chunk_id"]: c for c in chunks}
    sources = [by_id[c["chunk_id"]] for c in valid if c["chunk_id"] in by_id]
    return {
        "answer": answer,
        "citations": valid,
        "sources": sources,
        "confidence": confidence,
    }
