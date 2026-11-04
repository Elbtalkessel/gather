"""Tests for Git operations, with the subprocess layer stubbed out."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from gather import git as git_module
from gather.errors import ForbiddenError, NoRemoteError
from gather.git import Git, current_branch, sync_existing
from gather.process import ProcessError, Result
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


class ScriptedProcess:
    """A ``Process`` stand-in whose responses are queued by the test."""

    calls: ClassVar[list[ScriptedProcess]] = []
    script: ClassVar[list[tuple[int, str, str]]] = []

    def __init__(self, *args: str, **kwargs: object) -> None:
        self.args = args
        ScriptedProcess.calls.append(self)

    def run(self) -> Result:
        code, out, err = ScriptedProcess.script.pop(0)
        return Result(self.args, code, out, err)

    def checked(self) -> Result:
        result = self.run()
        if not result.ok:
            raise ProcessError(result)
        return result


@pytest.fixture
def stub_scripted(monkeypatch: pytest.MonkeyPatch) -> None:
    ScriptedProcess.script = []
    ScriptedProcess.calls = []
    monkeypatch.setattr(git_module, "Process", ScriptedProcess)


def test_sync_existing_raises_no_remote_when_origin_missing(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "gather"
    ScriptedProcess.script = [(128, "", "fatal: 'origin' does not appear to be a git repository")]
    with pytest.raises(NoRemoteError):
        sync_existing(repo)


def test_sync_existing_raises_forbidden_on_access_denied(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "gather"
    ScriptedProcess.script = [
        (0, "git@gitea.x.home.arpa:owner/repo.git", ""),  # remote get-url origin
        (128, "", "Permission denied (publickey).\nfatal: Could not read from remote repository."),  # fetch
    ]
    with pytest.raises(ForbiddenError):
        sync_existing(repo)


def test_sync_existing_propagates_other_fetch_failures(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "gather"
    ScriptedProcess.script = [
        (0, "git@gitea.x.home.arpa:owner/repo.git", ""),  # remote get-url origin
        (1, "", "some unrelated git error"),  # fetch
    ]
    with pytest.raises(ProcessError):
        sync_existing(repo)


def test_sync_existing_skips_empty_checkout(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "gather"
    ScriptedProcess.script = [
        (0, "git@gitea.x.home.arpa:owner/repo.git", ""),  # remote get-url origin
        (0, "", ""),  # fetch
        (0, "master", ""),  # symbolic-ref --short HEAD
        (128, "", "fatal: Needed a single revision"),  # rev-parse --verify HEAD
        (128, "", "fatal: Needed a single revision"),  # rev-parse --verify origin/master
    ]
    sync_existing(repo)
    called = [call.args for call in ScriptedProcess.calls]
    assert not any("merge" in args for args in called)
    assert not any("checkout" in args for args in called)


def test_sync_existing_adopts_remote_branch_for_empty_checkout(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "gather"
    ScriptedProcess.script = [
        (0, "git@gitea.x.home.arpa:owner/repo.git", ""),  # remote get-url origin
        (0, "", ""),  # fetch
        (0, "master", ""),  # symbolic-ref --short HEAD
        (128, "", "fatal: Needed a single revision"),  # rev-parse --verify HEAD
        (0, "abc123", ""),  # rev-parse --verify origin/master
        (0, "", ""),  # checkout -B master origin/master
    ]
    sync_existing(repo)
    called = [call.args for call in ScriptedProcess.calls]
    assert (
        "git",
        "-C",
        str(repo),
        "checkout",
        "-B",
        "master",
        "origin/master",
    ) in called
    assert not any("merge" in args for args in called)
