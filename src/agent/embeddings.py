"""Embedding wrapper using Ollama Python client.

The original implementation incorrectly used the non‑existent ``ollama embed`` CLI
command, which always raised ``unknown command "embed"`` and forced the fallback
mock vector of length 3.  The correct API is the ``ollama.embed`` function from the
``ollama`` Python package.  This module now calls that API and returns the 1024‑dimensional
vectors produced by the ``bge-m3`` model.  If the call fails (e.g. Ollama not running
or the model not downloaded) a ``RuntimeError`` is raised so the caller can handle the
failure explicitly.
"""

from __future__ import annotations

import json
from typing import List

import ollama

_MODEL = "bge-m3"


def _run_ollama(texts: List[str]) -> List[List[float]]:
    """Call the Ollama Python client to generate embeddings.

    ``ollama.embed`` returns a dict with an ``embeddings`` key containing a list of
    vectors.  We extract and return that list.
    """
    result = ollama.embed(model=_MODEL, input=texts)
    # Expected format: {"embeddings": [[float, ...], ...]}
    return result["embeddings"]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Return embedding vectors for the given ``texts``.

    If the Ollama service cannot generate embeddings, a ``RuntimeError`` is raised –
    callers (e.g. the ingestion pipeline) should decide whether to abort or retry.
    """
    try:
        return _run_ollama(texts)
    except Exception as exc:
        raise RuntimeError(
            "No se pudo generar embeddings con bge-m3; verificá que Ollama esté corriendo y el modelo descargado"
        ) from exc

