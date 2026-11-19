"""The privacy promise, turned into tests that can fail.

Three guarantees, three different kinds of proof:

1. ``test_probe_detects_a_simulated_leak`` is the positive control. Without it,
   a broken hook passes every other test in this file silently.
2. ``test_*_stays_on_loopback`` run the real code paths under the hook.
3. ``test_refuses_a_public_bind`` / ``test_wipe_*`` cover the two places where a
   privacy claim usually dies: a copy-pasted ``--host`` and a delete button
   that leaves the originals on disk.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agent.net import LocalOnlyViolation, assert_loopback_host, is_loopback_address
from agent.wipe import DB_SIDECARS, wipe_state

PROBE = Path(__file__).resolve().parent / "privacy_probe.py"


def _run_probe(mode: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.lower().endswith("_proxy")}
    env["OLLAMA_HOST"] = "http://127.0.0.1:11434"
    env["NO_PROXY"] = "*"
    return subprocess.run(
        [sys.executable, str(PROBE), mode],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


# --- the probe itself -------------------------------------------------------


def test_probe_detects_a_simulated_leak():
    """Positive control: if this passes clean, the hook is not watching."""
    proc = _run_probe("leak")
    assert proc.returncode == 3, f"expected a caught leak, got {proc.returncode}\n{proc.stdout}{proc.stderr}"
    payload = json.loads(proc.stdout)
    assert payload["violations"], "the hook saw nothing while connecting outward"


def test_storage_path_makes_no_network_calls():
    proc = _run_probe("db")
    assert proc.returncode == 0, f"{proc.stdout}{proc.stderr}"


def test_ollama_client_stays_on_loopback():
    """Refused connections are fine; leaving the host is not."""
    proc = _run_probe("ollama")
    assert proc.returncode == 0, f"{proc.stdout}{proc.stderr}"


# --- the bind guard ---------------------------------------------------------


def test_refuses_a_public_bind():
    for host in ("0.0.0.0", "192.168.1.10", "10.0.0.1", "::", "example.com"):
        with pytest.raises(LocalOnlyViolation):
            assert_loopback_host(host)


def test_accepts_a_loopback_bind():
    for host in ("127.0.0.1", "::1", "localhost"):
        assert assert_loopback_host(host) == host


def test_address_judgement():
    assert is_loopback_address(("127.0.0.1", 11434))
    assert is_loopback_address(("::1", 8000))
    assert is_loopback_address(("localhost", 80))
    assert is_loopback_address("/tmp/socket.sock")
    assert is_loopback_address(None)
    assert not is_loopback_address(("example.com", 443))
    assert not is_loopback_address(("8.8.8.8", 53))


# --- the delete button ------------------------------------------------------


def test_wipe_removes_db_sidecars_and_originals(tmp_path):
    db = tmp_path / "index.db"
    db.write_bytes(b"db")
    for suffix in DB_SIDECARS:
        (tmp_path / f"index.db{suffix}").write_bytes(b"leftover")

    output = tmp_path / "output"
    output.mkdir()
    (output / "recordatorio.md").write_text("contrato")
    (output / "nested").mkdir()
    (output / "nested" / "borrador.md").write_text("clausula")

    private = tmp_path / "private"
    private.mkdir()
    (private / "contrato.pdf").write_bytes(b"%PDF-1.4 secret")

    removed = wipe_state(db, output, private)

    assert removed == {"db": 1, "sidecar": 3, "output": 2, "private": 1}
    assert not db.exists()
    for suffix in DB_SIDECARS:
        assert not (tmp_path / f"index.db{suffix}").exists()
    assert list(output.rglob("*")) == []
    assert list(private.rglob("*")) == []
    assert output.is_dir() and private.is_dir()


def test_wipe_is_idempotent(tmp_path):
    removed = wipe_state(tmp_path / "missing.db", tmp_path / "missing-output")
    assert removed == {"db": 0, "sidecar": 0, "output": 0, "private": 0}
