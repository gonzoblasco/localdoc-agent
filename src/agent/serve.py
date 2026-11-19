"""Guarded server entry point.

``uvicorn src.agent.ui:app`` binds 127.0.0.1 by default, but nothing stops
someone from passing ``--host 0.0.0.0``. This runner makes the bind an explicit
decision the code can refuse, so the local-only promise survives a copy-pasted
command line.
"""

from __future__ import annotations

import os
import sys

from .net import LocalOnlyViolation, assert_loopback_host


def _parse(argv: list[str]) -> tuple[str, int]:
    host = os.environ.get("NIDO_HOST", "127.0.0.1")
    port = int(os.environ.get("NIDO_PORT", "8000"))
    it = iter(argv)
    for arg in it:
        if arg in ("--host", "-h"):
            host = next(it, host)
        elif arg in ("--port", "-p"):
            port = int(next(it, port))
        elif arg.startswith("--host="):
            host = arg.split("=", 1)[1]
        elif arg.startswith("--port="):
            port = int(arg.split("=", 1)[1])
    return host, port


def main(argv: list[str] | None = None) -> int:
    host, port = _parse(list(sys.argv[1:] if argv is None else argv))
    try:
        assert_loopback_host(host)
    except LocalOnlyViolation as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    import uvicorn

    uvicorn.run(os.environ.get("NIDO_APP", "src.agent.ui:app"), host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
