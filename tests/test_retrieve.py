from pathlib import Path

import pytest

from agent.db import init_db
from agent.embeddings import embed_texts
from agent.ingest import ingest_file
from agent.retrieve import hybrid_search, vector_search


@pytest.fixture()
def conn(tmp_path):
    db_path = tmp_path / "test.db"
    demo = Path(__file__).parents[1] / "data" / "demo"
    for doc in demo.iterdir():
        ingest_file(doc, db_path)
    c = init_db(db_path)
    yield c
    c.close()


def test_hybrid_search_development(conn):
    results = hybrid_search(conn, "Desarrollo", top_k=5)
    assert results
    assert any("desarrollo" in (r["text"] or "").lower() for r in results)
    assert results == sorted(results, key=lambda r: r["score"], reverse=True)


def test_vector_search_returns_knn(conn):
    q = embed_texts(["factura"])[0]
    results = vector_search(conn, q, top_k=3)
    assert len(results) == 3
    assert all("distance" in r for r in results)
    assert results == sorted(results, key=lambda r: r["distance"])
