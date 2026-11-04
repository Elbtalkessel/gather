"""Tests for Git operations, with the subprocess layer stubbed out."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from gather import git as git_module
from gather.git import Git, current_branch, sync_existing
from gather.process import Result
from gather.remote import Remote

REMOTE = Remote.parse("git@gitea.x.home.arpa:python/gather.git")


class FakeProcess:
    calls: ClassVar[list[FakeProcess]] = []

    def __init__(self, *args: str, **kwargs: object) -> None:
        self.args = args
        self.cwd = kwargs.get("cwd")
        self.timeout = kwargs.get("timeout")
        FakeProcess.calls.append(self)

    def run(self) -> Result:
        return Result(self.args, 0, "main", "")

    def checked(self) -> Result:
        return self.run()


@pytest.fixture(autouse=True)
def stub_process(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeProcess.calls = []
    monkeypatch.setattr(git_module, "Process", FakeProcess)


def commands() -> list[tuple[str, ...]]:
    return [call.args for call in FakeProcess.calls]


def test_sync_clones_when_absent(tmp_path: Path) -> None:
    repo = tmp_path / "gather"
    Git(REMOTE).sync(repo)
    assert commands()[0][:3] == ("git", "clone", REMOTE.origin)


def test_sync_fetches_and_fast_forwards_when_present(tmp_path: Path) -> None:
    repo = tmp_path / "gather"
    (repo / ".git").mkdir(parents=True)
    Git(REMOTE).sync(repo)
    assert ("git", "-C", str(repo), "fetch", "origin") in commands()
    assert ("git", "-C", str(repo), "merge", "--ff-only", "origin/main") in commands()


def test_sync_does_not_use_pull(tmp_path: Path) -> None:
    repo = tmp_path / "gather"
    (repo / ".git").mkdir(parents=True)
    Git(REMOTE).sync(repo)
    assert not any("pull" in args for args in commands())


def test_sync_existing_fetches_and_fast_forwards(tmp_path: Path) -> None:
    repo = tmp_path / "gather"
    sync_existing(repo)
    assert ("git", "-C", str(repo), "fetch", "origin") in commands()
    assert ("git", "-C", str(repo), "merge", "--ff-only", "origin/main") in commands()


def test_current_branch(tmp_path: Path) -> None:
    repo = tmp_path / "gather"
    assert current_branch(repo) == "main"
    assert commands()[-1][:4] == ("git", "-C", str(repo), "rev-parse")


def test_worktree_add_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    root = tmp_path / "worktrees"
    path = Git(REMOTE).worktree_add(repo, root, "feature/x")
    assert path == root / "feature/x"
    assert ("git", "-C", str(repo), "worktree", "add", str(path), "-b", "feature/x") in commands()


def test_worktree_add_is_idempotent_when_exists(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    root = tmp_path / "worktrees"
    branch = "feature/x"
    path = root / branch
    path.mkdir(parents=True)
    result = Git(REMOTE).worktree_add(repo, root, branch)
    assert result == path
    assert commands() == []
