"""Ingestion utilities for the local agent.

Provides simple extraction from PDF (via ``pypdf``) and Markdown/TXT, chunking by headings, and
persists the results using the database helpers.
"""

from __future__ import annotations

import pathlib
import re
from typing import List, Mapping

from pypdf import PdfReader

from .db import init_db, insert_document, insert_chunk
from .embeddings import embed_texts
import json


def extract_text(path: str | pathlib.Path) -> List[str]:
    p = pathlib.Path(path)
    if p.suffix.lower() == ".pdf":
        reader = PdfReader(p)
        pages = []
        for page in reader.pages:
            txt = page.extract_text() or ""
            if not txt.strip():
                raise ValueError("PDF sin texto seleccionable; OCR fuera de alcance")
            pages.append(txt)
        return pages
    else:
        return [p.read_text(encoding="utf-8")]


_HEADING_RE = re.compile(r"^(#+)\s+(.*)$", re.MULTILINE)


def _split_into_sections(pages: List[str]) -> List[Mapping[str, str]]:
    sections: List[Mapping[str, str]] = []
    current_title = ""
    current_parts: List[str] = []
    for page in pages:
        for line in page.splitlines():
            m = _HEADING_RE.match(line)
            if m:
                if current_parts:
                    sections.append({"title": current_title, "text": "\n".join(current_parts)})
                current_title = m.group(2).strip()
                current_parts = []
            else:
                current_parts.append(line)
    if current_parts:
        sections.append({"title": current_title, "text": "\n".join(current_parts)})
    return sections


def chunk_by_clause(pages: List[str]) -> List[dict]:
    sections = _split_into_sections(pages)
    chunks: List[dict] = []
    page_index = 0
    for sec in sections:
        while page_index < len(pages) and sec["text"] not in pages[page_index]:
            page_index += 1
        chunks.append(
            {
                "text": sec["text"].strip(),
                "page": page_index + 1 if page_index < len(pages) else None,
                "section": sec["title"],
                "clause": f"{sec['title'].replace(' ', '_') or 'intro'}",
            }
        )
    return chunks


def ingest_file(path: str | pathlib.Path, db_path: str | pathlib.Path) -> None:
    pages = extract_text(path)
    chunks = chunk_by_clause(pages)
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)
    conn = init_db(db_path)
    doc_id = insert_document(conn, str(path), pathlib.Path(path).stem)
    for chunk, emb in zip(chunks, embeddings):
        # Store embedding as JSON for mock compatibility
        emb_json = json.dumps(emb) if not isinstance(emb, (bytes, bytearray)) else emb
        insert_chunk(
            conn,
            doc_id,
            chunk["text"],
            chunk.get("page"),
            chunk.get("section"),
            chunk.get("clause"),
            emb_json,
        )
    conn.close()

