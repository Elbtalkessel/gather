"""Tests for shared data-returning operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from gather import ops
from gather.errors import ForbiddenError, GatherError, NoRemoteError
from gather.layout import Layout


def test_resolve_remote_rejects_non_leaf(tmp_path: Path) -> None:
    (tmp_path / "gitea.x.home.arpa").mkdir()
    with pytest.raises(GatherError):
        ops.resolve_remote(tmp_path, "gitea.x.home.arpa")


def test_resolve_remote_rejects_missing_repo(tmp_path: Path) -> None:
    with pytest.raises(GatherError):
        ops.resolve_remote(tmp_path, "gitea.x.home.arpa/python/gather")


def test_resolve_remote_allow_missing_defaults_to_https(tmp_path: Path) -> None:
    remote = ops.resolve_remote(
        tmp_path, "gitea.x.home.arpa/python/gather", allow_missing=True
    )
    assert remote.host == "gitea.x.home.arpa"
    assert remote.owner == "python"
    assert remote.repo == "gather"
    assert remote.proto == "https"


def test_resolve_remote_accepts_full_url(tmp_path: Path) -> None:
    remote = ops.resolve_remote(tmp_path, "git@gitea.x.home.arpa:python/gather.git")
    assert remote.host == "gitea.x.home.arpa"
    assert remote.owner == "python"
    assert remote.repo == "gather"
    assert remote.proto == "ssh"


def _repo(root: Path, name: str = "repo") -> Path:
    path = root / "gitea.x.home.arpa" / "python" / name
    (path / ".git").mkdir(parents=True)
    return path


def _stub_sync(monkeypatch: pytest.MonkeyPatch, exc: Exception) -> None:
    monkeypatch.setattr(ops, "discover", lambda layout, scope=(): [_repo(layout.root)])

    def boom(path: Path) -> None:
        raise exc

    monkeypatch.setattr(ops, "sync_existing", boom)


def test_sync_reports_no_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_sync(monkeypatch, NoRemoteError("no origin"))
    assert ops.sync(Layout(tmp_path)) == [
        {"path": "gitea.x.home.arpa/python/repo", "status": "no remote or forbidden"}
    ]


def test_sync_reports_forbidden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_sync(monkeypatch, ForbiddenError("forbidden"))
    assert ops.sync(Layout(tmp_path)) == [
        {"path": "gitea.x.home.arpa/python/repo", "status": "no remote or forbidden"}
    ]


def test_sync_reports_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ops, "discover", lambda layout, scope=(): [_repo(layout.root)])
    monkeypatch.setattr(ops, "sync_existing", lambda path: None)
    assert ops.sync(Layout(tmp_path)) == [
        {"path": "gitea.x.home.arpa/python/repo", "status": "ok"}
    ]


def test_list_repos_skips_wikis(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _repo(tmp_path, "repo")
    _repo(tmp_path, "repo.wiki")
    monkeypatch.setattr(ops, "current_branch", lambda path: "main")
    assert ops.list_repos(Layout(tmp_path)) == [
        {"path": "gitea.x.home.arpa/python/repo", "branch": "main"}
    ]
