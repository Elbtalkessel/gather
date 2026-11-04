"""Tests for repository discovery and scope parsing."""

from __future__ import annotations

from pathlib import Path

from gather.discover import discover, parse_scope
from gather.layout import Layout


def _repo(root: Path, host: str, owner: str, name: str) -> Path:
    path = root / host / owner / name
    (path / ".git").mkdir(parents=True)
    return path


def test_parse_scope_none() -> None:
    assert parse_scope(None) == ()


def test_parse_scope_host() -> None:
    assert parse_scope("gitea.x.home.arpa") == ("gitea.x.home.arpa",)


def test_parse_scope_leaf() -> None:
    assert parse_scope("gitea.x.home.arpa/python/gather") == (
        "gitea.x.home.arpa",
        "python",
        "gather",
    )


def test_parse_scope_strips_slashes() -> None:
    assert parse_scope("/gitea.x.home.arpa/python/") == (
        "gitea.x.home.arpa",
        "python",
    )


def test_discover_everything(tmp_path: Path) -> None:
    layout = Layout(tmp_path)
    _repo(tmp_path, "gitea.x.home.arpa", "python", "gather")
    _repo(tmp_path, "gitea.x.home.arpa", "nix", "nixos")
    _repo(tmp_path, "github.com", "foo", "bar")
    assert len(discover(layout)) == 3


def test_discover_host_scope(tmp_path: Path) -> None:
    layout = Layout(tmp_path)
    _repo(tmp_path, "gitea.x.home.arpa", "python", "gather")
    _repo(tmp_path, "gitea.x.home.arpa", "nix", "nixos")
    _repo(tmp_path, "github.com", "foo", "bar")
    repos = discover(layout, ("gitea.x.home.arpa",))
    assert {r.name for r in repos} == {"gather", "nixos"}


def test_discover_leaf_scope(tmp_path: Path) -> None:
    layout = Layout(tmp_path)
    _repo(tmp_path, "gitea.x.home.arpa", "python", "gather")
    _repo(tmp_path, "gitea.x.home.arpa", "python", "other")
    repos = discover(layout, ("gitea.x.home.arpa", "python", "gather"))
    assert [r.name for r in repos] == ["gather"]


def test_discover_excludes_worktrees_and_cache(tmp_path: Path) -> None:
    layout = Layout(tmp_path)
    _repo(tmp_path, "gitea.x.home.arpa", "python", "gather")
    (tmp_path / "worktrees" / "gitea.x.home.arpa" / "python" / "gather" / "feature" / "x" / ".git").mkdir(parents=True)
    (tmp_path / ".gather" / "gitea.x.home.arpa" / "python" / "gather" / ".git").mkdir(parents=True)
    repos = discover(layout)
    assert [r.name for r in repos] == ["gather"]


def test_discover_includes_wikis(tmp_path: Path) -> None:
    layout = Layout(tmp_path)
    _repo(tmp_path, "gitea.x.home.arpa", "python", "gather")
    _repo(tmp_path, "gitea.x.home.arpa", "python", "gather.wiki")
    assert {r.name for r in discover(layout)} == {"gather", "gather.wiki"}


def test_discover_deeper_scope_is_empty(tmp_path: Path) -> None:
    layout = Layout(tmp_path)
    _repo(tmp_path, "gitea.x.home.arpa", "python", "gather")
    assert discover(layout, ("gitea.x.home.arpa", "python", "gather", "extra")) == []
