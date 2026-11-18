import sys, pathlib, sqlite3

# Ensure the project root (containing the ``src`` package) is on the import path.
project_root = pathlib.Path(__file__).parents[2]
# Add the ``src`` directory so that ``import agent`` works
sys.path.insert(0, str(project_root / "src"))

from agent.ingest import ingest_file
from agent.db import get_chunks, init_db


def test_ingest_demo(tmp_path: pathlib.Path):
    db_file = tmp_path / "test.db"
    demo_dir = pathlib.Path(__file__).parents[1].parent / "data" / "demo"
    for doc in demo_dir.iterdir():
        ingest_file(doc, db_file)

    conn = init_db(db_file)
    docs = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    assert docs == 3
    total_chunks = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    assert total_chunks >= 3
    rows = get_chunks(conn, "Desarrollo")
    assert any("Desarrollo" in r[1] for r in rows)
    vec = conn.execute("SELECT embedding FROM chunks LIMIT 1").fetchone()[0]
    import json
    parsed = json.loads(vec)
    # The embedding should be a 1024‑dimensional vector as returned by ``ollama.embed``.
    assert isinstance(parsed, list) and len(parsed) == 1024
    conn.close()

