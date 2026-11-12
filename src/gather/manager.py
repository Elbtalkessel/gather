"""High-level orchestration: setup, wiki sync, worktrees, info."""

from __future__ import annotations

import os
import socket
from collections.abc import Sequence
from pathlib import Path

from gather.devenv import Devenv
from gather.git import Git
from gather.layout import Layout
from gather.process import Process
from gather.remote import Remote
from gather.wiki import merge_wikis

#: The instance-wide wiki merged into every ALL.md by default. Override with
#: the GATHER_INSTANCE_WIKI env var; set it to an empty string to disable the
#: default merge.
INSTANCE_WIKI = os.environ.get(
    "GATHER_INSTANCE_WIKI", "git@gitea.x.home.arpa:kb/gitea.git"
)


class Manager:
    """Orchestrates one remote's repo, wiki, and worktrees under a :class:`Layout`."""

    def __init__(self, layout: Layout, remote: Remote) -> None:
        self.layout = layout
        self.remote = remote
        self.git = Git(remote)

    @property
    def repo_path(self) -> Path:
        return self.layout.repo(self.remote)

    @property
    def wiki_path(self) -> Path:
        return self.layout.repo(self.remote.wiki)

    @property
    def worktree_root(self) -> Path:
        return self.layout.worktrees(self.remote)

    def setup(self) -> Path:
        self.git.sync(self.repo_path)
        return self.repo_path

    def wiki_sync(self) -> Path:
        Git(self.remote.wiki).sync(self.wiki_path)
        return self.wiki_path

    def worktree_add(self, branch: str) -> Path:
        path = self.git.worktree_add(self.repo_path, self.worktree_root, branch)
        Devenv(path).setup()
        return path

    def worktree_remove(self, branch: str) -> None:
        self.git.worktree_remove(self.repo_path, self.worktree_root, branch)

    def info_fields(self) -> dict[str, str]:
        """Return the resolved paths and remotes as a dict."""
        return {
            "username": Process("git", "config", "--get", "user.name").run().out,
            "email": Process("git", "config", "--get", "user.email").run().out,
            "hostname": socket.gethostname(),
            "repo": str(self.repo_path),
            "wiki": str(self.wiki_path),
            "worktrees": str(self.worktree_root),
            "repo remote": self.remote.origin,
            "wiki remote": self.remote.wiki.origin,
        }

    def info(self) -> None:
        for name, value in self.info_fields().items():
            print(f"{name}: {value}")


def sync_wikis(layout: Layout, main: Remote, extras: Sequence[str]) -> Path:
    """Sync the project wiki, the instance wiki, and every extra wiki, then
    merge them into ALL.md.

    The instance wiki (:data:`INSTANCE_WIKI`, by default the shared
    ``kb/gitea`` wiki) is always merged unless ``GATHER_INSTANCE_WIKI`` is set
    to an empty string. ``extras`` holds additional repo URLs whose *wikis*
    should be merged. The merged view is written to a derived cache location,
    never inside a wiki repo.
    """
    urls = [url for url in (INSTANCE_WIKI, *extras) if url]
    remotes: list[Remote] = []
    seen: set[str] = set()
    for remote in [main, *(Remote.parse(url) for url in urls)]:
        if remote.origin not in seen:
            seen.add(remote.origin)
            remotes.append(remote)

    wikis: list[tuple[Remote, Path]] = []
    for remote in remotes:
        wiki_remote = remote.wiki
        wiki_path = layout.repo(wiki_remote)
        Git(wiki_remote).sync(wiki_path)
        wikis.append((wiki_remote, wiki_path))

    output = layout.cache(main) / "ALL.md"
    merge_wikis(wikis, output)
    return output
