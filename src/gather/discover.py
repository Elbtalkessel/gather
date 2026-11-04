"""Discover repositories in the projects tree."""

from __future__ import annotations

from pathlib import Path

from gather.layout import Layout

_REPO_DEPTH = 3  # host/owner/name
_EXCLUDED = {"worktrees", ".gather"}


def parse_scope(url: str | None) -> tuple[str, ...]:
    """Turn an optional ``-u`` value into scope parts (``()`` = everything)."""
    if url is None:
        return ()
    return tuple(part for part in url.strip("/").split("/") if part)


def discover(layout: Layout, scope: tuple[str, ...] = ()) -> list[Path]:
    """Return every git repo path (repo and ``.wiki``) under a scope.

    Repos live exactly three levels deep — ``<host>/<owner>/<name>`` — so
    discovery is a bounded walk from the scope prefix down to depth 3.
    """
    if len(scope) > _REPO_DEPTH:
        return []
    base = layout.root.joinpath(*scope)
    repos: list[Path] = []
    _walk(base, _REPO_DEPTH - len(scope), repos)
    return repos


def _walk(directory: Path, levels: int, acc: list[Path]) -> None:
    if levels == 0:
        if (directory / ".git").exists():
            acc.append(directory)
        return
    if not directory.is_dir():
        return
    for child in sorted(directory.iterdir()):
        if child.is_dir() and child.name not in _EXCLUDED:
            _walk(child, levels - 1, acc)
