"""Optional devenv integration for freshly created worktrees."""

from __future__ import annotations

from pathlib import Path

from gather.process import Process


class Devenv:
    """Trigger a devenv activation, but only when the repo declares one."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def is_available(self) -> bool:
        return (self.root / "devenv.nix").exists()

    def setup(self) -> None:
        if not self.is_available():
            return
        # First activation builds the environment and can take minutes, so use
        # a generous timeout.
        Process(
            "devenv", "shell", "--", "echo", "devenv ready",
            cwd=str(self.root),
            timeout=60.0,
        ).checked()
