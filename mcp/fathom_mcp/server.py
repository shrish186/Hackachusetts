"""Build and run the Fathom MCP server with the official `mcp` Python SDK.

The server exposes the eight Fathom tools (design.md section 7) over stdio so the
in-app agent and Kiro can both call them. Tools are thin wrappers over the pure
functions in :mod:`fathom_mcp.tools`; input is validated with pydantic and
``pydantic.ValidationError`` is converted into a clear, structured error payload
rather than being allowed to break the transport.

SDK compatibility
-----------------
The official SDK renamed ``FastMCP`` (v1) to ``MCPServer`` (v2). This module
imports whichever is available so the skeleton runs on either line.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from . import tools as _tools

# The server class was renamed FastMCP -> MCPServer between SDK v1 and v2.
# Import whichever this environment provides so the skeleton is version-agnostic.
try:  # SDK v2.x (current stable)
    from mcp.server.mcpserver import MCPServer as _ServerClass  # type: ignore
except ModuleNotFoundError:  # SDK v1.x
    from mcp.server.fastmcp import FastMCP as _ServerClass  # type: ignore


SERVER_NAME = "fathom"
SERVER_INSTRUCTIONS = (
    "Fathom's data/risk/route tools for Massachusetts' working waterfront. "
    "Every factual claim an agent makes must come from one of these tool "
    "results and be cited. NOTE: this server is a SKELETON — all tools return "
    "clearly-labelled placeholder data (placeholder=true) until the "
    "deterministic engine is wired in."
)


def _wrap(fn: Callable[..., dict[str, Any]]) -> Callable[..., dict[str, Any]]:
    """Wrap a tool so validation errors become a structured, non-fatal result.

    Keeps the original ``__name__``/``__doc__`` so the SDK registers the tool
    with the correct name and description.
    """

    def wrapper(**kwargs: Any) -> dict[str, Any]:
        try:
            return fn(**kwargs)
        except ValidationError as exc:
            return {
                "placeholder": True,
                "tool": fn.__name__,
                "error": "invalid_input",
                "detail": exc.errors(include_url=False),
            }

    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    # Preserve the annotations so the SDK can derive the tool's input schema.
    wrapper.__annotations__ = dict(getattr(fn, "__annotations__", {}))
    return wrapper


def build_server() -> Any:
    """Create the MCP server and register all eight Fathom tools.

    Returns:
        A configured server instance (``MCPServer``/``FastMCP``) ready to ``run``.
    """
    server = _ServerClass(name=SERVER_NAME, instructions=SERVER_INSTRUCTIONS)
    for tool_fn in _tools.TOOLS:
        server.tool(name=tool_fn.__name__)(_wrap(tool_fn))
    return server


def main() -> None:
    """Entry point for ``python -m fathom_mcp``: run the server over stdio."""
    server = build_server()
    server.run(transport="stdio")
