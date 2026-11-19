"""Run a workload under a socket audit hook and report non-loopback traffic.

Why a subprocess: ``sys.addaudithook`` cannot be removed once installed, so
auditing inside pytest would also audit the test runner. This script is spawned
by ``tests/test_privacy.py`` and speaks JSON on stdout.

Exit codes
    0  clean: every socket target stayed on loopback
    3  at least one non-loopback target
    4  the workload itself raised before finishing
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from agent.net import is_loopback_address  # noqa: E402

VIOLATIONS: list[dict] = []

_EVENTS = {
    "socket.connect",
    "socket.getaddrinfo",
    "socket.gethostbyname",
    "socket.gethostbyaddr",
}


def _hook(event: str, args: tuple) -> None:
    if event not in _EVENTS:
        return
    if event == "socket.connect":
        target = args[1] if len(args) > 1 else None
    else:
        target = args[0] if args else None
    if not is_loopback_address(target):
        VIOLATIONS.append({"event": event, "target": repr(target)[:200]})


def _workload_db() -> None:
    """The full read path, with embeddings stubbed: proves storage is offline."""
    import tempfile
    from pathlib import Path

    from agent import db, retrieve

    retrieve.embed_texts = lambda texts: [[0.0] * 1024 for _ in texts]
    with tempfile.TemporaryDirectory() as tmp:
        conn = db.init_db(Path(tmp) / "probe.db")
        db.insert_document(conn, "probe.pdf", "Probe")
        db.list_documents(conn)
        db.count_chunks(conn)
        retrieve.hybrid_search(conn, "clausula", top_k=3)
        conn.close()


def _workload_ollama() -> None:
    """The Ollama client's connection path. Refused connections are still local.

    Deliberately does NOT call ``chat``/``embed`` with a real model: when a
    model is missing, the *Ollama server* pulls it from the registry, and that
    traffic happens in another process where this hook cannot see it. That gap
    is real and is documented in the README instead of hidden here.
    """
    import ollama

    client = ollama.Client(host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434"), timeout=2)
    try:
        client.list()
    except Exception:
        pass


def _workload_leak() -> None:
    """Positive control: this MUST be caught, or the hook is broken."""
    import socket

    try:
        socket.create_connection(("example.com", 80), timeout=1)
    except Exception:
        pass


_WORKLOADS = {"db": _workload_db, "ollama": _workload_ollama, "leak": _workload_leak}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in _WORKLOADS:
        print(json.dumps({"error": f"usage: privacy_probe.py {{{'|'.join(_WORKLOADS)}}}"}))
        return 4

    os.environ.setdefault("OLLAMA_HOST", "http://127.0.0.1:11434")
    sys.addaudithook(_hook)

    try:
        _WORKLOADS[sys.argv[1]]()
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}", "violations": VIOLATIONS}))
        return 4

    print(json.dumps({"violations": VIOLATIONS, "clean": not VIOLATIONS}))
    return 3 if VIOLATIONS else 0


if __name__ == "__main__":
    raise SystemExit(main())
