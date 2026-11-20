"""Reads config/models.yaml. Model IDs live there (or in an env override), never in code."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_ENV = "SOR_MODELS_CONFIG"
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "models.yaml"


@lru_cache(maxsize=1)
def load() -> dict[str, Any]:
    data = yaml.safe_load(Path(os.environ.get(CONFIG_ENV, DEFAULT_PATH)).read_text())
    if not isinstance(data, dict) or "models" not in data:
        raise ValueError("models config: expected a 'models' section")
    return data


def region() -> str:
    return str(load().get("region", "us-east-2"))


def model(role: str) -> dict[str, Any]:
    """The entry for a role, with `id` replaced by its env override when one is set."""
    entry: dict[str, Any] = dict(load()["models"][role])
    override = entry.get("env_override")
    if override and os.environ.get(override):
        entry["id"] = os.environ[override]
    return entry


def model_id(role: str) -> str:
    return str(model(role)["id"])
