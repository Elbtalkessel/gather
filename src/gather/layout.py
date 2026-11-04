"""On-disk layout resolution under the projects root."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gather.remote import Remote


@dataclass(frozen=True)
class Layout:
    """Maps remotes to their on-disk locations, namespaced by host.

    The projects root (``$XDG_PROJECTS_DIR`` or ``~/Projects``) holds::

        <root>/<host>/<owner>/<repo>             reference clone
        <root>/<host>/<owner>/<repo>.wiki        wiki (first-class sibling)
        <root>/worktrees/<host>/<owner>/<repo>   worktrees
        <root>/.gather/<host>/<owner>/<repo>     derived artifacts (ALL.md)
    """

    root: Path

    def repo(self, remote: Remote) -> Path:
        return self.root / remote.path

    def worktrees(self, remote: Remote) -> Path:
        return self.root / "worktrees" / remote.path

    def cache(self, remote: Remote) -> Path:
        return self.root / ".gather" / remote.path
