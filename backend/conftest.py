"""Pytest configuration for the backend test suite.

Ensures ``backend/`` is on ``sys.path`` so ``import app...`` works regardless of
the directory pytest is invoked from, and points ingest at the repo root.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Make config/ and data/ discoverable even when cwd differs.
os.environ.setdefault("FATHOM_ROOT", str(REPO_ROOT))
