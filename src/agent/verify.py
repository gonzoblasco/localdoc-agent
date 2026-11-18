"""Verificación determinística de citas."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Tuple


def _normalize(text: str) -> str:
    """Colapsa whitespace para comparar substrings."""
    return re.sub(r"\s+", " ", text).strip()


def verify_citations(
    citations: Iterable[Dict[str, Any]],
    chunks_by_id: Dict[int, str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Separa citas válidas de inválidas.

    Una cita es válida si ``quote`` es un substring exacto (normalizado) del
    chunk correspondiente.
    """
    valid: List[Dict[str, Any]] = []
    invalid: List[Dict[str, Any]] = []
    for cit in citations:
        cid = cit.get("chunk_id")
        quote = cit.get("quote", "")
        chunk = chunks_by_id.get(cid, "")
        if not chunk:
            invalid.append(cit)
            continue
        if _normalize(quote) in _normalize(chunk):
            valid.append(cit)
        else:
            invalid.append(cit)
    return valid, invalid
