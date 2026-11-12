"""Tests for CLI printing behaviour."""

from __future__ import annotations

from pathlib import Path

import pytest

from gather import cli as cli_module
from gather import ops
from gather.errors import NoRemoteError


def _repo(root: Path, name: str = "repo") -> Path:
    path = root / "gitea.x.home.arpa" / "python" / name
    (path / ".git").mkdir(parents=True)
    return path


def _stub_sync(monkeypatch: pytest.MonkeyPatch, exc: Exception) -> None:
    monkeypatch.setattr(ops, "discover", lambda layout, scope=(): [_repo(layout.root)])
    monkeypatch.setattr(ops, "ensure_clean", lambda path, force=False: None)

    def boom(path: Path) -> None:
        raise exc

    monkeypatch.setattr(ops, "sync_existing", boom)


def test_sync_prints_no_remote_or_forbidden(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli_module, "_PROJECTS_DIR", str(tmp_path))
    _stub_sync(monkeypatch, NoRemoteError("no origin"))
    assert cli_module.main(["--sync"]) == 0
    assert "no remote or forbidden" in capsys.readouterr().out
