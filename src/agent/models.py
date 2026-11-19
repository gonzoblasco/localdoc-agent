"""Model selection and the local/cloud boundary."""

from __future__ import annotations

import os

LOCAL_MODEL = os.environ.get("NIDO_LOCAL_MODEL", "gemma4:12b-mlx")
CLOUD_MODEL = os.environ.get("NIDO_CLOUD_MODEL", "deepseek-v4.1-flash:cloud")
DEFAULT_MODEL = os.environ.get("NIDO_MODEL", LOCAL_MODEL)


def model_mode(model: str | None) -> str:
    """``cloud`` for an Ollama ``:cloud`` model, ``local`` otherwise."""
    return "cloud" if (model or "").rstrip().endswith(":cloud") else "local"


def model_label(model: str | None) -> str:
    return "Cloud" if model_mode(model) == "cloud" else "Local"
