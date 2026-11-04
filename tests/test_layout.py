"""Tests for Layout path resolution."""

from __future__ import annotations

from pathlib import Path

from gather.layout import Layout
from gather.remote import Remote

ROOT = Path("/home/u/Projects")
REMOTE = Remote.parse("git@gitea.x.home.arpa:python/gather.git")


def test_repo_path_has_host_prefix() -> None:
    layout = Layout(ROOT)
    assert layout.repo(REMOTE) == ROOT / "gitea.x.home.arpa" / "python" / "gather"


def test_wiki_is_first_class_sibling() -> None:
    layout = Layout(ROOT)
    assert layout.repo(REMOTE.wiki) == ROOT / "gitea.x.home.arpa" / "python" / "gather.wiki"


def test_worktrees_have_host_prefix() -> None:
    layout = Layout(ROOT)
    assert layout.worktrees(REMOTE) == ROOT / "worktrees" / "gitea.x.home.arpa" / "python" / "gather"


def test_cache_is_gitignored_location() -> None:
    layout = Layout(ROOT)
    assert layout.cache(REMOTE) == ROOT / ".gather" / "gitea.x.home.arpa" / "python" / "gather"
