"""Module entry point so ``python -m fathom_mcp`` starts the server.

This matches the command already configured (but disabled) in
``.kiro/settings/mcp.json``.
"""

from __future__ import annotations

from .server import main

if __name__ == "__main__":
    main()
