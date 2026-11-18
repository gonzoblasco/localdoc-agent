"""Hybrid retrieval utilities (BM25 + sqlite-vec KNN + RRF)."""

from __future__ import annotations

import json
import re
import sqlite3
from typing import Any, Dict, List

from .embeddings import embed_texts


def _fts_query(query: str) -> str:
    """Build a safe FTS5 query from free text.

    FTS5 treats punctuation like ``?`` and ``¿`` as syntax. We keep only word
    characters and join the terms with ``OR`` so a natural-language question
    does not crash the query.
    """
    terms = re.findall(r"\w+", query, flags=re.UNICODE)
    if not terms:
        return '""'
    return " OR ".join(f'"{t}"' for t in terms)


def bm25_search(
    conn: sqlite3.Connection, query: str, top_k: int = 20
) -> List[Dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT c.id, c.text, c.page, c.section, c.clause, d.title
        FROM chunks c
        JOIN chunks_fts f ON c.id = f.rowid
        JOIN documents d ON d.id = c.document_id
        WHERE f.text MATCH ?
        ORDER BY bm25(chunks_fts) ASC
        LIMIT ?
        """,
        (_fts_query(query), top_k),
    ).fetchall()
    return [
        {
            "chunk_id": r[0],
            "text": r[1],
            "page": r[2],
            "section": r[3],
            "clause": r[4],
            "document": r[5],
        }
        for r in rows
    ]


def vector_search(
    conn: sqlite3.Connection, query_embedding: List[float], top_k: int = 20
) -> List[Dict[str, Any]]:
    q = json.dumps(query_embedding)
    rows = conn.execute(
        """
        SELECT cv.chunk_id, cv.distance, c.text, c.page, c.section, c.clause, d.title
        FROM chunks_vec cv
        JOIN chunks c ON c.id = cv.chunk_id
        JOIN documents d ON d.id = c.document_id
        WHERE cv.embedding MATCH ? AND k = ?
        ORDER BY cv.distance ASC
        """,
        (q, top_k),
    ).fetchall()
    return [
        {
            "chunk_id": r[0],
            "text": r[2],
            "page": r[3],
            "section": r[4],
            "clause": r[5],
            "document": r[6],
            "distance": r[1],
        }
        for r in rows
    ]


def hybrid_search(
    conn: sqlite3.Connection, query: str, top_k: int = 8, k_rrf: int = 60
) -> List[Dict[str, Any]]:
    bm25_results = bm25_search(conn, query, top_k=top_k * 2)
    query_vec = embed_texts([query])[0]
    vec_results = vector_search(conn, query_vec, top_k=top_k * 2)

    def rank_map(results: List[Dict[str, Any]]) -> Dict[int, int]:
        return {r["chunk_id"]: i + 1 for i, r in enumerate(results)}

    bm25_rank = rank_map(bm25_results)
    vec_rank = rank_map(vec_results)
    meta = {r["chunk_id"]: r for r in bm25_results + vec_results}
    fused: List[Dict[str, Any]] = []
    for cid in set(bm25_rank) | set(vec_rank):
        score = 0.0
        if cid in bm25_rank:
            score += 1.0 / (k_rrf + bm25_rank[cid])
        if cid in vec_rank:
            score += 1.0 / (k_rrf + vec_rank[cid])
        fused.append({**meta[cid], "score": score})
    fused.sort(key=lambda x: x["score"], reverse=True)
    return fused[:top_k]


def get_chunk(conn: sqlite3.Connection, chunk_id: int) -> Dict[str, Any]:
    row = conn.execute(
        "SELECT c.id, c.text, c.page, c.section, c.clause, d.title "
        "FROM chunks c JOIN documents d ON d.id = c.document_id "
        "WHERE c.id = ?",
        (chunk_id,),
    ).fetchone()
    if not row:
        raise KeyError(f"Chunk {chunk_id} not found")
    return {
        "chunk_id": row[0],
        "text": row[1],
        "page": row[2],
        "section": row[3],
        "clause": row[4],
        "document": row[5],
    }
