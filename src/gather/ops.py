"""Shared operations returning data; the CLI prints, the MCP server returns."""

from __future__ import annotations

from pathlib import Path

from gather.discover import discover, parse_scope
from gather.errors import (
    DirtyReferenceError,
    ForbiddenError,
    GatherError,
    NoRemoteError,
)
from gather.git import current_branch, ensure_clean, sync_existing
from gather.layout import Layout
from gather.remote import Remote


def _is_url(value: str) -> bool:
    return value.startswith(("git@", "https://", "http://"))


def _scope(url: str | None) -> tuple[str, ...]:
    """Resolve a ``-u`` value to a scope for bulk operations."""
    if url is None:
        return ()
    if _is_url(url):
        raise GatherError(f"expected a path prefix, not a url: {url!r}")
    return parse_scope(url)


def resolve_remote(root: Path, url: str, *, allow_missing: bool = False) -> Remote:
    """Resolve a full url to a :class:`Remote`, or a ``host/owner/repo`` path to
    the remote of an already-setup checkout.

    With ``allow_missing``, a path with no local checkout resolves to an https
    remote so ``--setup`` can clone it.
    """
    if _is_url(url):
        return Remote.parse(url)
    parts = parse_scope(url)
    if len(parts) != 3:
        raise GatherError(f"expected <host>/<owner>/<repo>, got {url!r}")
    path = root.joinpath(*parts)
    if (path / ".git").exists():
        return Remote.from_path(path)
    if allow_missing:
        return Remote.parse(url)
    raise GatherError(f"repository {path} does not exist; run --setup first")


def list_repos(layout: Layout, url: str | None = None) -> list[dict[str, str]]:
    """Return ``{path, branch}`` for every repo (not wiki) under the scope."""
    result: list[dict[str, str]] = []
    for path in discover(layout, _scope(url)):
        if path.name.endswith(".wiki"):
            continue
        result.append(
            {
                "path": str(path.relative_to(layout.root)),
                "branch": current_branch(path),
            }
        )
    return result


def sync(layout: Layout, url: str | None = None, *, force: bool = False) -> list[dict[str, str]]:
    """Fetch and fast-forward every repo under the scope.

    A repo is first healed onto its default branch and refused if dirty (unless
    ``force`` discards), so a stray off-default or dirty reference clone fails
    loudly instead of half-fast-forwarding. A repo with no ``origin`` or whose
    remote rejects access is reported in its status field
    (``"no remote or forbidden"``) rather than raised.
    """
    result: list[dict[str, str]] = []
    for path in discover(layout, _scope(url)):
        status = "ok"
        try:
            ensure_clean(path, force=force)
            sync_existing(path)
        except DirtyReferenceError:
            status = "dirty"
        except (NoRemoteError, ForbiddenError):
            status = "no remote or forbidden"
        result.append(
            {
                "path": str(path.relative_to(layout.root)),
                "status": status,
            }
        )
    return result
