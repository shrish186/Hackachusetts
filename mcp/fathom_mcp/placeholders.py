"""Helpers for building clearly-labelled placeholder tool responses.

Every tool in this skeleton returns data shaped like the real response WILL be,
but with unmistakable markers so no caller (human or agent) treats it as real:

- ``placeholder: true`` on the top level of every response.
- ``source: "PLACEHOLDER — fathom_mcp skeleton"`` wherever a real source/url goes.
- a human-readable ``note`` describing what the real tool will compute.

This keeps the citation-guard honest: placeholder facts are visibly not sourced.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

#: Marker written into every ``source``/``source_url`` field of placeholder data.
PLACEHOLDER_SOURCE = "PLACEHOLDER — fathom_mcp skeleton (no real data)"


def _utcnow_iso() -> str:
    """Current UTC time as an ISO-8601 string (all times are UTC internally)."""
    return datetime.now(timezone.utc).isoformat()


def placeholder_response(tool: str, note: str, **payload: Any) -> dict[str, Any]:
    """Wrap tool output with the standard placeholder envelope.

    Args:
        tool: The tool name, echoed back for traceability.
        note: Plain-language description of what the real tool will return.
        **payload: The (placeholder) domain payload for this tool.

    Returns:
        A dict with ``placeholder``/``tool``/``note``/``generated_at`` plus the
        supplied payload. The ``placeholder`` flag is always ``True`` here.
    """
    return {
        "placeholder": True,
        "tool": tool,
        "note": note,
        "source": PLACEHOLDER_SOURCE,
        "generated_at": _utcnow_iso(),
        **payload,
    }
