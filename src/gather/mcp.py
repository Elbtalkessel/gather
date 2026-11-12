"""MCP server exposing every gather operation as a tool.

The MCP SDK is imported lazily (inside :func:`build_server`), so ``import
gather.mcp`` never requires the optional ``mcp`` extra. Each tool reuses the
same :mod:`gather.ops` and :class:`~gather.manager.Manager` code paths as the
CLI; only the transport (a printed line vs. a returned structure) differs.
"""

from __future__ import annotations

import functools
import importlib
import os
import sys
from pathlib import Path
from typing import Any

from gather import ops
from gather.errors import GatherError
from gather.layout import Layout
from gather.manager import Manager, sync_wikis

_PROJECTS_DIR = os.environ.get("XDG_PROJECTS_DIR", "~/Projects")

_MISSING_HINT = (
    "the 'mcp' extra is not installed; install it with `pip install 'gather[mcp]'`"
)


def _import_mcp() -> tuple[Any, Any]:
    """Import ``MCPServer`` and ``ToolError`` without a module-top dependency."""
    try:
        server = importlib.import_module("mcp.server")
        exceptions = importlib.import_module("mcp.server.mcpserver.exceptions")
    except ImportError as exc:
        raise ImportError(_MISSING_HINT) from exc
    return server.MCPServer, exceptions.ToolError


def build_server() -> Any:
    """Build an :class:`MCPServer` registering one tool per CLI operation."""
    MCPServer, ToolError = _import_mcp()
    root = Path(_PROJECTS_DIR).expanduser()
    layout = Layout(root)

    def guard(fn: Any) -> Any:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except GatherError as exc:
                raise ToolError(str(exc)) from exc

        return wrapper

    mcp = MCPServer("gather")

    @mcp.tool()
    @guard
    def setup(url: str, force: bool = False) -> str:
        """Clone or update the reference repository; returns its path."""
        remote = ops.resolve_remote(root, url, allow_missing=True)
        return str(Manager(layout, remote).setup(force=force))

    @mcp.tool()
    @guard
    def sync_wiki(url: str, extra_urls: list[str] | None = None) -> str:
        """Sync the project wiki, instance wiki, and extra wikis into ALL.md; returns its path."""
        remote = ops.resolve_remote(root, url)
        return str(sync_wikis(layout, remote, extra_urls or []))

    @mcp.tool()
    @guard
    def info(url: str) -> dict[str, str]:
        """Return the resolved paths and remotes."""
        remote = ops.resolve_remote(root, url)
        return Manager(layout, remote).info_fields()

    @mcp.tool()
    @guard
    def list_repos(scope: str | None = None) -> list[dict[str, str]]:
        """List repositories under the scope with their current branch."""
        return ops.list_repos(layout, scope)

    @mcp.tool()
    @guard
    def sync(scope: str | None = None, force: bool = False) -> list[dict[str, str]]:
        """Fetch and fast-forward every repository under the scope."""
        return ops.sync(layout, scope, force=force)

    @mcp.tool()
    @guard
    def worktree_create(url: str, branch: str) -> str:
        """Create a worktree for a branch; returns its path."""
        remote = ops.resolve_remote(root, url)
        return str(Manager(layout, remote).worktree_add(branch))

    @mcp.tool()
    @guard
    def worktree_remove(url: str, branch: str) -> str:
        """Remove a worktree; returns a status string."""
        remote = ops.resolve_remote(root, url)
        Manager(layout, remote).worktree_remove(branch)
        return "worktree removed"

    return mcp


def main() -> int:
    """Entry point for the ``gather-mcp`` script (stdio server)."""
    try:
        server = build_server()
    except ImportError as exc:
        print(f"gather-mcp: error: {exc}", file=sys.stderr)
        return 1
    server.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
