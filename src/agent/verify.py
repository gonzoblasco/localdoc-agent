"""Verificación determinística de citas y de los literales del answer."""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Any, Dict, Iterable, List, Tuple


_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
_MONTH_RE = "|".join(sorted(_MONTHS, key=len, reverse=True))

_DATE_ISO_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DATE_SLASH_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_DATE_MONTH_FIRST_RE = re.compile(
    rf"\b({_MONTH_RE})\s+(\d{{1,2}})(?:,)?\s+(\d{{4}})\b", re.IGNORECASE
)
_DATE_DAY_FIRST_RE = re.compile(
    rf"\b(\d{{1,2}})\s+({_MONTH_RE})\s+(\d{{4}})\b", re.IGNORECASE
)
_CURRENCY_RE = re.compile(r"[$€£]\s?(\d[\d.,]*)")
_PERCENT_RE = re.compile(r"\b(\d+(?:[.,]\d+)?)\s?%")
_CLAUSE_RE = re.compile(
    r"\b(?:clause|section|cláusula|clausula)\s+(\d+(?:\.\d+)*)\b", re.IGNORECASE
)


def _normalize(text: str) -> str:
    """Normaliza diferencias de extracción, no solo whitespace.

    NFKC convierte ligaduras (fi, fl) en letras. Los PDFs también traen
    comillas tipográficas, soft hyphens, NBSP y palabras cortadas por salto de
    línea; todo eso produce rechazos falsos si se compara el string crudo.
    """
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\u00ad", "")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = text.replace("\u00a0", " ")
    text = (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )
    return re.sub(r"\s+", " ", text).strip()


def _valid_date(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def date_candidates(text: str) -> set[str]:
    """Fechas en cualquier formato reconocido, canonizadas a YYYY-MM-DD."""
    found: set[str] = set()
    for y, m, d in _DATE_ISO_RE.findall(text or ""):
        iso = _valid_date(int(y), int(m), int(d))
        if iso:
            found.add(iso)
    for d, m, y in _DATE_SLASH_RE.findall(text or ""):
        iso = _valid_date(int(y), int(m), int(d))
        if iso:
            found.add(iso)
    for month_name, d, y in _DATE_MONTH_FIRST_RE.findall(text or ""):
        month = _MONTHS.get(month_name.lower())
        if month:
            iso = _valid_date(int(y), month, int(d))
            if iso:
                found.add(iso)
    for d, month_name, y in _DATE_DAY_FIRST_RE.findall(text or ""):
        month = _MONTHS.get(month_name.lower())
        if month:
            iso = _valid_date(int(y), month, int(d))
            if iso:
                found.add(iso)
    return found


def _parse_amount(raw: str) -> float | None:
    s = re.sub(r"[^\d.,]", "", raw).strip(".,")
    if not s:
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(".", "")
        s = s.replace(",", ".") if len(s.rsplit(",", 1)[1]) == 2 else s.replace(",", "")
    elif "." in s:
        s = s.replace(",", "")
        s = s.replace(".", ".") if len(s.rsplit(".", 1)[1]) == 2 else s.replace(".", "")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def amount_candidates(text: str) -> set[str]:
    found: set[str] = set()
    for raw in _CURRENCY_RE.findall(text or ""):
        value = _parse_amount(raw)
        if value is not None:
            found.add(f"{value:.2f}")
    for raw in _PERCENT_RE.findall(text or ""):
        try:
            value = float(raw.replace(",", "."))
        except ValueError:
            continue
        found.add(f"{value:.2f}%")
    return found


def clause_candidates(text: str) -> set[str]:
    return {m.group(1) for m in _CLAUSE_RE.finditer(text or "")}


def extract_literals(answer: str) -> List[Dict[str, str]]:
    """Devuelve fechas, montos, porcentajes y cláusulas del answer.

    Una entrada por valor canónico; el raw se conserva para trazabilidad.
    """
    literals: List[Dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, raw: str, canonical: str) -> None:
        key = (kind, canonical)
        if key not in seen:
            seen.add(key)
            literals.append({"kind": kind, "raw": raw, "canonical": canonical})

    for iso in date_candidates(answer):
        add("date", iso, iso)
    for amount in amount_candidates(answer):
        add("amount", amount, amount)
    for clause in clause_candidates(answer):
        add("clause", clause, clause)
    return literals


def verify_answer_literals(
    answer: str,
    valid_citations: Iterable[Dict[str, Any]],
    method: str | None = None,
) -> List[Dict[str, str]]:
    """Literales del answer que no aparecen en ninguna cita válida.

    ``method="deterministic_calc"`` se salta: un total derivado de dos citas
    correctas no tiene por qué aparecer literalmente en una de ellas. El camino
    determinístico ya verifica sus operandos.
    """
    if not answer or method == "deterministic_calc":
        return []

    quotes = " ".join(str(c.get("quote", "")) for c in valid_citations)
    quote_dates = date_candidates(quotes)
    quote_amounts = amount_candidates(quotes)
    quote_clauses = clause_candidates(quotes)
    normalized_quotes = _normalize(quotes)

    missing: List[Dict[str, str]] = []
    for literal in extract_literals(answer):
        kind = literal["kind"]
        canonical = literal["canonical"]
        if kind == "date":
            supported = canonical in quote_dates
        elif kind == "amount":
            supported = canonical in quote_amounts
        else:
            supported = canonical in quote_clauses
        if not supported and _normalize(literal["raw"]) in normalized_quotes:
            supported = True
        if not supported:
            missing.append(literal)
    return missing


def verify_citations(
    citations: Iterable[Dict[str, Any]],
    chunks_by_id: Dict[int, str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Separa citas válidas de inválidas.

    Una cita es válida si ``quote`` es un substring del chunk correspondiente
    después de normalizar diferencias de extracción.
    """
    valid: List[Dict[str, Any]] = []
    invalid: List[Dict[str, Any]] = []
    for cit in citations:
        cid = cit.get("chunk_id")
        try:
            cid = int(cid)
        except (TypeError, ValueError):
            pass
        quote = cit.get("quote", "")
        chunk = chunks_by_id.get(cid, "")
        if not chunk and cid is not None:
            chunk = chunks_by_id.get(str(cid), "")
        if not chunk:
            invalid.append(cit)
            continue
        if _normalize(quote) in _normalize(chunk):
            valid.append(cit)
        else:
            invalid.append(cit)
    return valid, invalid
