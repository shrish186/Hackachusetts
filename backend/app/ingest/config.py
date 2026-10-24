"""Shared helpers to locate the repo root and load config/data files (Lane A).

Keeping path resolution in one place means ingest modules work the same from
the repo root, from backend/, and from the test runner.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Return the repository root (the directory that contains config/ and data/).

    Resolution order:
    1. ``FATHOM_ROOT`` environment variable, if set.
    2. Walk upward from this file until a directory with both ``config`` and
       ``data`` is found.
    """
    env = os.environ.get("FATHOM_ROOT")
    if env:
        return Path(env).resolve()

    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "config").is_dir() and (parent / "data").is_dir():
            return parent
    # Fallback: three levels up (backend/app/ingest -> repo root).
    return here.parents[3]


def config_path(*parts: str) -> Path:
    """Path to a file under ``config/``."""
    return repo_root().joinpath("config", *parts)


def data_path(*parts: str) -> Path:
    """Path to a file under ``data/`` (relative segments)."""
    return repo_root().joinpath("data", *parts)


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file into a dict."""
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"expected a mapping at the top of {path}, got {type(data)}")
    return data


@lru_cache(maxsize=1)
def study_area_config() -> dict[str, Any]:
    """Load ``config/study_area.yaml`` (bbox, cell size, land mask path)."""
    return load_yaml(config_path("study_area.yaml"))
