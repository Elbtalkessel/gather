"""Tests for wiki-sync orchestration in :mod:`gather.manager`."""

from __future__ import annotations

from pathlib import Path

import pytest

from gather import manager as manager_module
from gather.layout import Layout
from gather.manager import Manager, sync_wikis
from gather.remote import Remote

MAIN = Remote.parse("git@gitea.x.home.arpa:python/gather.git")
MAIN_WIKI = "git@gitea.x.home.arpa:python/gather.wiki.git"
INSTANCE_WIKI = "git@gitea.x.home.arpa:kb/gitea.wiki.git"


@pytest.fixture
def merged_wikis(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Remote, Path]]:
    """Capture the ``(remote, path)`` pairs handed to :func:`merge_wikis`."""
    captured: list[tuple[Remote, Path]] = []

    class FakeGit:
        def __init__(self, remote: Remote) -> None:
            self.remote = remote

        def sync(self, path: Path) -> None:
            pass

    monkeypatch.setattr(manager_module, "Git", FakeGit)
    monkeypatch.setattr(
        manager_module,
        "merge_wikis",
        lambda wikis, output: captured.extend(wikis),
    )
    return captured


def test_sync_wikis_includes_instance_wiki_by_default(
    tmp_path: Path, merged_wikis: list[tuple[Remote, Path]]
) -> None:
    sync_wikis(Layout(tmp_path), MAIN, [])

    assert [remote.origin for remote, _ in merged_wikis] == [
        MAIN_WIKI,
        INSTANCE_WIKI,
    ]


def test_sync_wikis_dedupes_instance_wiki_when_repeated(
    tmp_path: Path, merged_wikis: list[tuple[Remote, Path]]
) -> None:
    sync_wikis(Layout(tmp_path), MAIN, [manager_module.INSTANCE_WIKI])

    assert [remote.origin for remote, _ in merged_wikis] == [
        MAIN_WIKI,
        INSTANCE_WIKI,
    ]


def test_sync_wikis_empty_instance_wiki_disables_default(
    tmp_path: Path,
    merged_wikis: list[tuple[Remote, Path]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(manager_module, "INSTANCE_WIKI", "")

    sync_wikis(Layout(tmp_path), MAIN, [])

    assert [remote.origin for remote, _ in merged_wikis] == [MAIN_WIKI]


class FakeGit:
    def __init__(self, remote: Remote) -> None:
        self.remote = remote

    def sync(self, path: Path) -> None:
        pass


def test_setup_ensures_clean_when_repo_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "gitea.x.home.arpa" / "python" / "gather"
    (repo / ".git").mkdir(parents=True)

    calls: list[tuple[str, Path, bool]] = []

    def fake_ensure_clean(path: Path, *, force: bool = False) -> None:
        calls.append(("ensure_clean", path, force))

    monkeypatch.setattr(manager_module, "ensure_clean", fake_ensure_clean)
    monkeypatch.setattr(manager_module, "Git", FakeGit)

    result = Manager(Layout(tmp_path), MAIN).setup()

    assert result == repo
    assert calls == [("ensure_clean", repo, False)]


def test_setup_forwards_force(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = tmp_path / "gitea.x.home.arpa" / "python" / "gather"
    (repo / ".git").mkdir(parents=True)

    calls: list[tuple[str, Path, bool]] = []

    def fake_ensure_clean(path: Path, *, force: bool = False) -> None:
        calls.append(("ensure_clean", path, force))

    monkeypatch.setattr(manager_module, "ensure_clean", fake_ensure_clean)
    monkeypatch.setattr(manager_module, "Git", FakeGit)

    Manager(Layout(tmp_path), MAIN).setup(force=True)

    assert calls == [("ensure_clean", repo, True)]


def test_setup_skips_ensure_clean_when_repo_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        manager_module, "ensure_clean", lambda path, force=False: calls.append("clean")
    )
    monkeypatch.setattr(manager_module, "Git", FakeGit)

    Manager(Layout(tmp_path), MAIN).setup()

    assert calls == []
