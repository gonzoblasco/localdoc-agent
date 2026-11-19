"""Delete everything the app ever wrote about the user's documents.

The old ``/delete`` endpoint unlinked ``index.db`` and emptied ``output/``. It
left three things behind, and every one of them is a copy of the private data:

* ``index.db-wal`` / ``index.db-shm`` — SQLite write-ahead log and shared
  memory file. A ``unlink`` of the main database does not touch them, and the
  WAL can hold recently written rows.
* ``data/private/`` — the uploaded originals. The ingest path copies each
  upload there before parsing it.
* ``output/`` subdirectories — the old loop only removed top-level files.

This module exists so the guarantee can be tested without HTTP.
"""

from __future__ import annotations

import shutil
from pathlib import Path

# SQLite sidecars. "-journal" is the rollback journal used when WAL is off.
DB_SIDECARS = ("-wal", "-shm", "-journal")


def wipe_state(db_path: Path, output_dir: Path, private_dir: Path | None = None) -> dict[str, int]:
    """Remove the database, its sidecars and every artifact directory.

    Returns a count per category so the caller (or a test) can show what was
    actually removed instead of trusting a 204.
    """
    db_path = Path(db_path)
    removed = {"db": 0, "sidecar": 0, "output": 0, "private": 0}

    if db_path.exists():
        db_path.unlink()
        removed["db"] = 1

    for suffix in DB_SIDECARS:
        sidecar = db_path.parent / f"{db_path.name}{suffix}"
        if sidecar.exists():
            sidecar.unlink()
            removed["sidecar"] += 1

    removed["output"] = _empty_dir(Path(output_dir))
    if private_dir is not None:
        removed["private"] = _empty_dir(Path(private_dir))

    return removed


def _empty_dir(path: Path) -> int:
    """Delete the directory and everything under it; recreate it empty."""
    if not path.exists():
        return 0
    count = sum(1 for _ in path.rglob("*") if _.is_file())
    shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return count
