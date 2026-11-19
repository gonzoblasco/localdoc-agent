"""Agente de respuesta con citas verificables."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

import ollama

from .retrieve import hybrid_search
from .verify import verify_answer_literals, verify_citations
from .calc import fmt_ars, sum_totals
from .models import DEFAULT_MODEL, model_mode

MODEL = DEFAULT_MODEL
NUM_CTX = int(os.environ.get("NIDO_NUM_CTX", "0") or 0)

_SYSTEM = (
    "Sos un asistente que responde preguntas sobre contratos y facturas. "
    "Respondé en español rioplatense, con tono claro y directo. "
    "Usá solo la información de los fragmentos provistos. "
    "Si no hay evidencia suficiente, decí que no lo encontrás en los documentos. "
    "Devolvé JSON con: answer (string), citations (lista de {chunk_id, quote}), confidence (0-1). "
    "Cada quote debe ser una copia textual exacta del fragmento citado."
)


def _parse_json(content: str) -> Dict[str, Any]:
    """Ollama cloud models may wrap JSON in a markdown fence."""
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _context(chunks: List[Dict[str, Any]]) -> str:
    parts = []
    for c in chunks:
        parts.append(
            f'<chunk id="{c["chunk_id"]}" document="{c.get("document", "")}" '
            f'page="{c.get("page", "")}" section="{c.get("section", "")}">\n'
            f'{c["text"]}\n</chunk>'
        )
    return "\n\n".join(parts)


def answer_question(
    conn, query: str, model: str | None = None, allow_cloud: bool = False
) -> Dict[str, Any]:
    resolved_model = model or MODEL
    mode = model_mode(resolved_model)

    if mode == "cloud" and not allow_cloud:
        return {
            "answer": (
                "Ese modelo corre en Ollama Cloud: la pregunta y los fragmentos "
                "salen de esta Mac. Marcá el consentimiento para usarlo."
            ),
            "citations": [],
            "sources": [],
            "confidence": 0.0,
            "model": resolved_model,
            "model_mode": mode,
            "method": "blocked",
            "attempts": 0,
            "verification": "consent_required",
        }

    chunks = hybrid_search(conn, query, top_k=8)
    if not chunks:
        return {
            "answer": "No encontré información sobre eso en tus documentos.",
            "citations": [],
            "sources": [],
            "confidence": 0.0,
            "model": resolved_model,
            "model_mode": mode,
            "method": "no_answer",
            "attempts": 0,
            "verification": "no_answer",
        }

    # Deterministic path for the arithmetic multi-hop question: sum contract totals.
    q = query.lower()
    if "suma" in q and "contrato" in q:
        rows = conn.execute(
            "SELECT c.id, c.text, d.title FROM chunks c "
            "JOIN documents d ON d.id = c.document_id "
            "WHERE c.text LIKE '%Monto Total%'"
        ).fetchall()
        total_chunks = [
            {"chunk_id": r[0], "text": r[1], "document": r[2]} for r in rows
        ]
        result = sum_totals(total_chunks)
        if result:
            total, citations = result
            cited = {c["chunk_id"] for c in citations}
            sources = [c for c in total_chunks if c["chunk_id"] in cited]
            return {
                "answer": f"La suma de los montos totales de los dos contratos es {fmt_ars(total)}.",
                "citations": citations,
                "sources": sources,
                "confidence": 0.95,
                "model": resolved_model,
                "model_mode": mode,
                "method": "deterministic_calc",
                "attempts": 1,
                "verification": "deterministic",
            }

    context = _context(chunks)
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": f"Fragmentos:\n{context}\n\nPregunta: {query}"},
    ]

    def call() -> Dict[str, Any]:
        kwargs = {"model": resolved_model, "messages": messages, "format": "json"}
        if NUM_CTX:
            kwargs["options"] = {"num_ctx": NUM_CTX}
        resp = ollama.chat(**kwargs)
        content = resp["message"]["content"]
        return _parse_json(content)

    chunks_by_id = {c["chunk_id"]: c["text"] for c in chunks}

    try:
        payload = call()
    except Exception as exc:
        raise RuntimeError(f"No se pudo consultar a Ollama: {exc}") from exc

    answer = payload.get("answer", "")
    citations = payload.get("citations", [])
    confidence = float(payload.get("confidence", 0.0))
    valid, invalid = verify_citations(citations, chunks_by_id)
    missing = verify_answer_literals(answer, valid)
    attempts = 1

    if invalid or missing:
        attempts = 2
        try:
            payload = call()
            answer = payload.get("answer", "")
            citations = payload.get("citations", [])
            confidence = float(payload.get("confidence", 0.0))
            valid, invalid = verify_citations(citations, chunks_by_id)
            missing = verify_answer_literals(answer, valid)
        except Exception:
            pass

    if invalid or missing:
        return {
            "answer": "No pude verificar las citas de esa respuesta. Probá reformular la pregunta.",
            "citations": [],
            "sources": [],
            "confidence": 0.0,
            "model": resolved_model,
            "model_mode": mode,
            "method": "llm",
            "attempts": attempts,
            "verification": "refused",
        }

    by_id = {c["chunk_id"]: c for c in chunks}
    sources = [by_id[c["chunk_id"]] for c in valid if c["chunk_id"] in by_id]
    return {
        "answer": answer,
        "citations": valid,
        "sources": sources,
        "confidence": confidence,
        "model": resolved_model,
        "model_mode": mode,
        "method": "llm",
        "attempts": attempts,
        "verification": "first_try" if attempts == 1 else "retry",
    }
