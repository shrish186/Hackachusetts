"""Pytest configuration for the Fathom backend test suite.

The backend models are imported as ``app.models...`` (see
``backend/app/models/__init__.py``), which requires the ``backend/`` directory
to be on ``sys.path``. Adding it here lets the tests run no matter which
directory pytest is invoked from (repo root or ``backend/``).
"""

from __future__ import annotations

import sys
from pathlib import Path

# backend/tests/conftest.py -> parents[1] == backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
