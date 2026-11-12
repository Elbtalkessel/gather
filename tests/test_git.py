"""Tests for Git operations, with the subprocess layer stubbed out."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pytest

from gather import git as git_module
from gather.errors import DirtyReferenceError, ForbiddenError, NoRemoteError
from gather.git import (
    Git,
    current_branch,
    default_branch,
    ensure_clean,
    sync_existing,
)
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


def _worktree_commands() -> list[tuple[str, ...]]:
    return [call.args for call in ScriptedProcess.calls]


def test_worktree_add_tracks_remote_branch_when_present(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "repo"
    root = tmp_path / "worktrees"
    branch = "feature/x"
    path = root / branch
    ScriptedProcess.script = [
        (0, "", ""),  # fetch origin
        (0, "abc123", ""),  # rev-parse --verify origin/feature/x
        (0, "", ""),  # worktree add path feature/x
    ]

    result = Git(REMOTE).worktree_add(repo, root, branch)

    assert result == path
    assert _worktree_commands() == [
        ("git", "-C", str(repo), "fetch", "origin"),
        ("git", "-C", str(repo), "rev-parse", "--verify", "origin/feature/x"),
        ("git", "-C", str(repo), "worktree", "add", str(path), "feature/x"),
    ]


def test_worktree_add_creates_branch_when_remote_missing(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "repo"
    root = tmp_path / "worktrees"
    branch = "feature/x"
    path = root / branch
    ScriptedProcess.script = [
        (0, "", ""),  # fetch origin
        (128, "", "fatal: Needed a single revision"),  # rev-parse --verify origin/feature/x
        (0, "", ""),  # worktree add path -b feature/x
    ]

    result = Git(REMOTE).worktree_add(repo, root, branch)

    assert result == path
    assert _worktree_commands() == [
        ("git", "-C", str(repo), "fetch", "origin"),
        ("git", "-C", str(repo), "rev-parse", "--verify", "origin/feature/x"),
        ("git", "-C", str(repo), "worktree", "add", str(path), "-b", "feature/x"),
    ]


def test_worktree_add_syncs_existing_worktree(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "repo"
    root = tmp_path / "worktrees"
    branch = "feature/x"
    path = root / branch
    path.mkdir(parents=True)
    ScriptedProcess.script = [
        (0, "", ""),  # fetch origin
        (0, "abc123", ""),  # rev-parse --verify origin/feature/x
        (0, "", ""),  # reset --hard origin/feature/x
    ]

    result = Git(REMOTE).worktree_add(repo, root, branch)

    assert result == path
    assert _worktree_commands() == [
        ("git", "-C", str(repo), "fetch", "origin"),
        ("git", "-C", str(repo), "rev-parse", "--verify", "origin/feature/x"),
        ("git", "-C", str(path), "reset", "--hard", "origin/feature/x"),
    ]


def test_worktree_add_leaves_existing_worktree_when_remote_missing(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "repo"
    root = tmp_path / "worktrees"
    branch = "feature/x"
    path = root / branch
    path.mkdir(parents=True)
    ScriptedProcess.script = [
        (0, "", ""),  # fetch origin
        (128, "", "fatal: Needed a single revision"),  # rev-parse --verify origin/feature/x
    ]

    result = Git(REMOTE).worktree_add(repo, root, branch)

    assert result == path
    assert _worktree_commands() == [
        ("git", "-C", str(repo), "fetch", "origin"),
        ("git", "-C", str(repo), "rev-parse", "--verify", "origin/feature/x"),
    ]


def test_default_branch_reads_origin_head(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "gather"
    ScriptedProcess.script = [(0, "refs/remotes/origin/master", "")]
    assert default_branch(repo) == "master"


def test_default_branch_empty_when_origin_head_missing(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "gather"
    ScriptedProcess.script = [(128, "", "")]
    assert default_branch(repo) == ""


def test_ensure_clean_checks_out_default_when_off_default(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "gather"
    ScriptedProcess.script = [
        (0, "feature/x", ""),  # rev-parse --abbrev-ref HEAD
        (0, "refs/remotes/origin/main", ""),  # symbolic-ref origin/HEAD
        (0, "", ""),  # status --short (clean)
        (0, "", ""),  # checkout main
    ]

    ensure_clean(repo)

    assert ("git", "-C", str(repo), "checkout", "main") in _worktree_commands()


def test_ensure_clean_on_default_and_clean_does_nothing(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "gather"
    ScriptedProcess.script = [
        (0, "main", ""),  # rev-parse --abbrev-ref HEAD
        (0, "refs/remotes/origin/main", ""),  # symbolic-ref origin/HEAD
        (0, "", ""),  # status --short (clean)
    ]

    ensure_clean(repo)

    assert not any("checkout" in args for args in _worktree_commands())


def test_ensure_clean_refuses_dirty(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "gather"
    ScriptedProcess.script = [
        (0, "feature/x", ""),  # rev-parse --abbrev-ref HEAD
        (0, "refs/remotes/origin/main", ""),  # symbolic-ref origin/HEAD
        (0, " M README.md", ""),  # status --short (dirty)
    ]

    with pytest.raises(DirtyReferenceError) as excinfo:
        ensure_clean(repo)

    assert "gather worktree -c feature/x" in str(excinfo.value)
    assert " M README.md" in str(excinfo.value)
    assert "--force" in str(excinfo.value)


def test_ensure_clean_force_discards_dirty(
    tmp_path: Path, stub_scripted: None
) -> None:
    repo = tmp_path / "gather"
    ScriptedProcess.script = [
        (0, "feature/x", ""),  # rev-parse --abbrev-ref HEAD
        (0, "refs/remotes/origin/main", ""),  # symbolic-ref origin/HEAD
        (0, " M README.md", ""),  # status --short (dirty)
        (0, "", ""),  # reset --hard
        (0, "", ""),  # clean -fd
        (0, "", ""),  # checkout main
    ]

    ensure_clean(repo, force=True)

    commands = _worktree_commands()
    assert ("git", "-C", str(repo), "reset", "--hard") in commands
    assert ("git", "-C", str(repo), "clean", "-fd") in commands
    assert ("git", "-C", str(repo), "checkout", "main") in commands
