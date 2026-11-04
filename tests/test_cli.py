"""Tests for CLI resolution and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from gather import cli as cli_module
from gather.cli import _cmd_sync, resolve_remote
from gather.errors import ForbiddenError, GatherError, NoRemoteError
from gather.layout import Layout


def test_resolve_remote_rejects_non_leaf(tmp_path: Path) -> None:
    (tmp_path / "gitea.x.home.arpa").mkdir()
    with pytest.raises(GatherError):
        resolve_remote(tmp_path, "gitea.x.home.arpa")


def test_resolve_remote_rejects_missing_repo(tmp_path: Path) -> None:
    with pytest.raises(GatherError):
        resolve_remote(tmp_path, "gitea.x.home.arpa/python/gather")


def test_resolve_remote_allow_missing_defaults_to_https(tmp_path: Path) -> None:
    remote = resolve_remote(
        tmp_path, "gitea.x.home.arpa/python/gather", allow_missing=True
    )
    assert remote.host == "gitea.x.home.arpa"
    assert remote.owner == "python"
    assert remote.repo == "gather"
    assert remote.proto == "https"


def _repo(root: Path, name: str = "repo") -> Path:
    path = root / "gitea.x.home.arpa" / "python" / name
    (path / ".git").mkdir(parents=True)
    return path


def _stub_sync(monkeypatch: pytest.MonkeyPatch, exc: Exception) -> None:
    monkeypatch.setattr(
        cli_module, "discover", lambda layout, scope=(): [_repo(layout.root)]
    )

    def boom(path: Path) -> None:
        raise exc

    monkeypatch.setattr(cli_module, "sync_existing", boom)


def test_cmd_sync_prints_no_remote_or_forbidden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stub_sync(monkeypatch, NoRemoteError("no origin"))
    _cmd_sync(Layout(tmp_path), None)
    assert "no remote or forbidden" in capsys.readouterr().out


def test_cmd_sync_handles_forbidden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _stub_sync(monkeypatch, ForbiddenError("forbidden"))
    _cmd_sync(Layout(tmp_path), None)
    assert "no remote or forbidden" in capsys.readouterr().out
