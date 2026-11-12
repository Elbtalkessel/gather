"""Tests for the MCP server's tool-to-operation mapping."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("mcp")

from mcp.server.mcpserver.exceptions import ToolError

from gather import mcp as mcp_module
from gather.errors import GatherError
from gather.remote import Remote

REMOTE = Remote.parse("git@gitea.x.home.arpa:python/gather.git")


def _fn(server: Any, name: str) -> Any:
    return server._tool_manager.get_tool(name).fn


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    monkeypatch.setattr(mcp_module, "_PROJECTS_DIR", str(tmp_path))
    return mcp_module.build_server()


def _stub_resolve_remote(monkeypatch: pytest.MonkeyPatch, calls: list[Any]) -> None:
    def resolve(root: Path, url: str, *, allow_missing: bool = False) -> Remote:
        calls.append(("resolve_remote", url, allow_missing))
        return REMOTE

    monkeypatch.setattr(mcp_module.ops, "resolve_remote", resolve)


def test_registers_seven_tools(server: Any) -> None:
    assert sorted(server._tool_manager._tools) == [
        "info",
        "list_repos",
        "setup",
        "sync",
        "sync_wiki",
        "worktree_create",
        "worktree_remove",
    ]


def test_setup_delegates_to_manager_setup(
    server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Any] = []
    _stub_resolve_remote(monkeypatch, calls)

    class FakeManager:
        def __init__(self, layout: Any, remote: Remote) -> None:
            self.remote = remote

        def setup(self, force: bool = False) -> Path:
            calls.append(("setup", self.remote, force))
            return Path("/projects/repo")

    monkeypatch.setattr(mcp_module, "Manager", FakeManager)

    result = _fn(server, "setup")("gitea.x.home.arpa/python/gather")

    assert result == "/projects/repo"
    assert calls == [
        ("resolve_remote", "gitea.x.home.arpa/python/gather", True),
        ("setup", REMOTE, False),
    ]


def test_sync_wiki_delegates_to_sync_wikis(
    server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Any] = []
    _stub_resolve_remote(monkeypatch, calls)

    def fake_sync_wikis(layout: Any, remote: Remote, extras: list[str]) -> Path:
        calls.append(("sync_wikis", remote, extras))
        return Path("/cache/ALL.md")

    monkeypatch.setattr(mcp_module, "sync_wikis", fake_sync_wikis)

    result = _fn(server, "sync_wiki")(
        "gitea.x.home.arpa/python/gather", ["https://x/kb/gitea.git"]
    )

    assert result == "/cache/ALL.md"
    assert calls == [
        ("resolve_remote", "gitea.x.home.arpa/python/gather", False),
        ("sync_wikis", REMOTE, ["https://x/kb/gitea.git"]),
    ]


def test_info_delegates_to_info_fields(
    server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Any] = []
    _stub_resolve_remote(monkeypatch, calls)

    class FakeManager:
        def __init__(self, layout: Any, remote: Remote) -> None:
            self.remote = remote

        def info_fields(self) -> dict[str, str]:
            calls.append(("info_fields", self.remote))
            return {"repo": "/projects/repo"}

    monkeypatch.setattr(mcp_module, "Manager", FakeManager)

    result = _fn(server, "info")("gitea.x.home.arpa/python/gather")

    assert result == {"repo": "/projects/repo"}
    assert calls == [
        ("resolve_remote", "gitea.x.home.arpa/python/gather", False),
        ("info_fields", REMOTE),
    ]


def test_list_repos_delegates_to_ops(server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []

    def fake_list_repos(layout: Any, scope: str | None) -> list[dict[str, str]]:
        calls.append(("list_repos", scope))
        return [{"path": "a/b", "branch": "main"}]

    monkeypatch.setattr(mcp_module.ops, "list_repos", fake_list_repos)

    result = _fn(server, "list_repos")("gitea.x.home.arpa")

    assert result == [{"path": "a/b", "branch": "main"}]
    assert calls == [("list_repos", "gitea.x.home.arpa")]


def test_sync_delegates_to_ops(server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []

    def fake_sync(
        layout: Any, scope: str | None, *, force: bool = False
    ) -> list[dict[str, str]]:
        calls.append(("sync", scope, force))
        return [{"path": "a/b", "status": "ok"}]

    monkeypatch.setattr(mcp_module.ops, "sync", fake_sync)

    result = _fn(server, "sync")("gitea.x.home.arpa")

    assert result == [{"path": "a/b", "status": "ok"}]
    assert calls == [("sync", "gitea.x.home.arpa", False)]


def test_worktree_create_delegates_to_manager(
    server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Any] = []
    _stub_resolve_remote(monkeypatch, calls)

    class FakeManager:
        def __init__(self, layout: Any, remote: Remote) -> None:
            self.remote = remote

        def worktree_add(self, branch: str) -> Path:
            calls.append(("worktree_add", self.remote, branch))
            return Path("/projects/worktrees") / branch

    monkeypatch.setattr(mcp_module, "Manager", FakeManager)

    result = _fn(server, "worktree_create")("gitea.x.home.arpa/python/gather", "feature/x")

    assert result == "/projects/worktrees/feature/x"
    assert calls == [
        ("resolve_remote", "gitea.x.home.arpa/python/gather", False),
        ("worktree_add", REMOTE, "feature/x"),
    ]


def test_worktree_remove_delegates_to_manager(
    server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Any] = []
    _stub_resolve_remote(monkeypatch, calls)

    class FakeManager:
        def __init__(self, layout: Any, remote: Remote) -> None:
            self.remote = remote

        def worktree_remove(self, branch: str) -> None:
            calls.append(("worktree_remove", self.remote, branch))

    monkeypatch.setattr(mcp_module, "Manager", FakeManager)

    result = _fn(server, "worktree_remove")("gitea.x.home.arpa/python/gather", "feature/x")

    assert result == "worktree removed"
    assert calls == [
        ("resolve_remote", "gitea.x.home.arpa/python/gather", False),
        ("worktree_remove", REMOTE, "feature/x"),
    ]


def test_gather_error_surfaces_as_tool_error(
    server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(root: Path, url: str, *, allow_missing: bool = False) -> Remote:
        raise GatherError("boom")

    monkeypatch.setattr(mcp_module.ops, "resolve_remote", boom)

    with pytest.raises(ToolError, match="boom"):
        _fn(server, "setup")("gitea.x.home.arpa/python/gather")
