"""Fathom MCP server package.

Exposes the eight Fathom tools (see `.kiro/specs/fathom/design.md`, section 7)
over the Model Context Protocol so that both the in-app LLM agent and Kiro can
query the same data/risk/route layer during development and at runtime.

This is a SKELETON. Every tool validates its input with pydantic and returns
clearly labelled PLACEHOLDER data. No tool computes real risk, routes, zones, or
conditions yet; the deterministic engine (Lane A/B) will back these later. Until
then every response carries ``"placeholder": true`` and a ``note`` so nothing can
be mistaken for real output.

Run it with::

    python -m fathom_mcp
"""

from __future__ import annotations

__all__ = ["__version__", "build_server", "main"]

__version__ = "0.1.0"

# Re-export lazily to avoid importing the `mcp` SDK (and its transport stack) at
# package import time; the models/tools modules are safe to import eagerly.
from .server import build_server, main  # noqa: E402
