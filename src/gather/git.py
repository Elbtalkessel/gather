"""Git operations, concurrency-safe for a shared reference/wiki clone."""

from __future__ import annotations

from pathlib import Path

from gather.process import Process
from gather.remote import Remote


class Git:
    """Wrap the git commands gather needs against a single remote."""

    def __init__(self, remote: Remote) -> None:
        self.remote = remote

    def clone(self, path: Path) -> None:
        Process("git", "clone", self.remote.origin, str(path), timeout=60.0).checked()

    def sync(self, path: Path) -> None:
        """Clone if absent, else fetch and fast-forward.

        Fast-forward (rather than ``git pull --rebase``) is deliberate: ``git
        pull`` races on its upstream resolution when several processes target
        the same clone concurrently. ``fetch`` + ``merge --ff-only`` is safe
        under concurrency and never rewrites local history — if the local
        branch has diverged it errors instead of silently rebasing.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        if (path / ".git").exists():
            self.fetch(path)
            self.fast_forward(path)
        else:
            self.clone(path)

    def fetch(self, path: Path) -> None:
        Process("git", "-C", str(path), "fetch", "origin").checked()

    def fast_forward(self, path: Path) -> None:
        branch = Process(
            "git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"
        ).checked().out
        Process("git", "-C", str(path), "merge", "--ff-only", f"origin/{branch}").checked()

    def worktree_add(self, repo: Path, root: Path, branch: str) -> Path:
        path = root / branch
        Process(
            "git", "-C", str(repo), "worktree", "add", str(path), "-b", branch
        ).checked()
        return path

    def worktree_remove(self, repo: Path, root: Path, branch: str) -> None:
        path = root / branch
        # Best-effort cleanup: report failures, don't raise.
        Process("git", "-C", str(repo), "worktree", "remove", str(path)).run()
        Process("git", "-C", str(repo), "branch", "-D", branch).run()
