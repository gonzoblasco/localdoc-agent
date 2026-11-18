"""Deterministic arithmetic helpers for contract totals."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

_TOTAL_RE = re.compile(
    r"(?:Monto\s+Total|Total\s+a\s+pagar|Total)\s*\**\s*:?\s*\**\s*\$\s?([\d\.]+(?:,\d{2})?)",
    re.IGNORECASE,
)


def parse_amount(raw: str) -> Optional[float]:
    cleaned = raw.strip().replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def fmt_ars(value: float) -> str:
    """Format a number as Argentine pesos: 23400 -> ``$23.400,00``."""
    s = f"{value:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"${s}"


def sum_totals(
    chunks: List[dict],
) -> Optional[Tuple[float, List[dict]]]:
    """Sum the ``Monto Total`` / ``Total a pagar`` of contract chunks.

    Returns ``(total, citations)`` or ``None`` if fewer than two contract
    totals are present.
    """
    by_chunk: Dict[int, Tuple[float, str]] = {}
    for c in chunks:
        doc = (c.get("document") or "").lower()
        if "contract" not in doc:
            continue
        for match in _TOTAL_RE.finditer(c["text"] or ""):
            value = parse_amount(match.group(1))
            if value is not None:
                by_chunk.setdefault(c["chunk_id"], (value, match.group(0)))

    if len(by_chunk) < 2:
        return None

    total = sum(v for v, _ in by_chunk.values())
    citations = [
        {"chunk_id": cid, "quote": quote}
        for cid, (_, quote) in by_chunk.items()
    ]
    return total, citations
