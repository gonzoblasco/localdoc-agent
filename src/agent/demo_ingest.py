"""Demo script to build the SQLite index from synthetic documents.
"""

from pathlib import Path

from .ingest import ingest_file
from .db import init_db


def main() -> None:
    project_root = Path(__file__).parents[2]
    db_path = project_root / "data" / "index.db"
    demo_dir = project_root / "data" / "demo"
    # Reset the index only if a fresh start is desired. We remove any existing file
    # before attempting ingestion, but if ingestion fails we keep the partially
    # built database so the user can inspect it.
    if db_path.exists():
        db_path.unlink()
    init_db(db_path).close()
    if not demo_dir.is_dir() or not any(demo_dir.iterdir()):
        raise FileNotFoundError(f"Demo directory '{demo_dir}' is missing or empty")
    try:
        for doc in demo_dir.iterdir():
            ingest_file(doc, db_path)
    except Exception as e:
        # Do not delete the DB; report the error so the user can debug.
        print(f"Error during ingestion: {e}")
        return
    conn = init_db(db_path)
    doc_cnt = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    chunk_cnt = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    print(f"Database created at {db_path}")
    print(f"Documents: {doc_cnt}, Chunks: {chunk_cnt}")
    conn.close()


if __name__ == "__main__":
    main()

