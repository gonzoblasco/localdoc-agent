"""Database utilities for the local agent.

Creates a SQLite database with:

* ``documents`` – metadata about each ingested file.
* ``chunks`` – each textual chunk with its embedding.
* ``chunks_fts`` – FTS5 virtual table for full-text search.
* ``chunks_vec`` – ``sqlite-vec`` virtual table for vector search, or a BLOB fallback.
"""

from __future__ import annotations

import pathlib
import sqlite3
from typing import List, Tuple

_BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    page INTEGER,
    section TEXT,
    clause TEXT,
    embedding BLOB
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text,
    content='chunks',
    content_rowid='id'
);
"""


def _load_vec_extension(conn: sqlite3.Connection) -> bool:
    """Load ``sqlite-vec``. Returns ``True`` on success."""
    try:
        import sqlite_vec

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except Exception:
        try:
            conn.enable_load_extension(False)
        except Exception:
            pass
        return False


def init_db(db_path: str | pathlib.Path) -> sqlite3.Connection:
    db_path = pathlib.Path(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    vec_ok = _load_vec_extension(conn)
    conn.executescript(_BASE_SCHEMA)
    if vec_ok:
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec "
            "USING vec0(chunk_id INTEGER PRIMARY KEY, embedding FLOAT[1024])"
        )
    else:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS chunks_vec "
            "(chunk_id INTEGER PRIMARY KEY, embedding BLOB)"
        )
    conn.commit()
    return conn


def insert_document(conn: sqlite3.Connection, path: str, title: str) -> int:
    cur = conn.execute(
        "INSERT INTO documents (path, title) VALUES (?, ?) "
        "ON CONFLICT(path) DO UPDATE SET title=excluded.title RETURNING id",
        (path, title),
    )
    return cur.fetchone()[0]


def insert_chunk(
    conn: sqlite3.Connection,
    doc_id: int,
    text: str,
    page: int | None,
    section: str | None,
    clause: str | None,
    embedding: bytes | str,
) -> int:
    cur = conn.execute(
        "INSERT INTO chunks (document_id, text, page, section, clause, embedding) "
        "VALUES (?,?,?,?,?,?)",
        (doc_id, text, page, section, clause, embedding),
    )
    chunk_id = cur.lastrowid
    conn.execute("INSERT INTO chunks_fts(rowid, text) VALUES (?,?)", (chunk_id, text))
    conn.execute(
        "INSERT INTO chunks_vec(chunk_id, embedding) VALUES (?,?)",
        (chunk_id, embedding),
    )
    conn.commit()
    return chunk_id


def get_chunks(conn: sqlite3.Connection, fts_query: str) -> List[Tuple[int, str, int, str, str]]:
    rows = conn.execute(
        "SELECT c.id, c.text, c.page, c.section, c.clause "
        "FROM chunks c JOIN chunks_fts f ON c.id = f.rowid "
        "WHERE f.text MATCH ?",
        (fts_query,),
    ).fetchall()
    return rows


def get_connection(db_path: str | pathlib.Path) -> sqlite3.Connection:
    """Open (or create) the index database with the schema applied."""
    return init_db(db_path)


def count_documents(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]


def count_chunks(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]


def list_documents(conn: sqlite3.Connection) -> List[Tuple[int, str, str, int]]:
    return conn.execute(
        "SELECT d.id, d.title, d.path, COUNT(c.id) "
        "FROM documents d LEFT JOIN chunks c ON c.document_id = d.id "
        "GROUP BY d.id ORDER BY d.id DESC"
    ).fetchall()
