"""Command-line interface for gather."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from gather.discover import discover, parse_scope
from gather.errors import ForbiddenError, GatherError, NoRemoteError
from gather.git import current_branch, sync_existing
from gather.layout import Layout
from gather.manager import Manager, sync_wikis
from gather.remote import Remote

_PROJECTS_DIR = os.environ.get("XDG_PROJECTS_DIR", "~/Projects")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gather",
        description=(
            "Bootstrap git repositories, their wikis, and worktrees in one "
            "opinionated, host-namespaced layout."
        ),
    )
    parser.add_argument(
        "-u",
        "--url",
        metavar="REPOSITORY_URL",
        help=(
            "full git url (for --setup) or a path prefix under the projects "
            "root: <host>, <host>/<owner>, or <host>/<owner>/<repo>"
        ),
    )
    parser.add_argument(
        "-s",
        "--setup",
        action="store_true",
        help="clone the reference repository",
    )
    parser.add_argument(
        "-w",
        "--wiki",
        nargs="*",
        metavar="EXTRA_URL",
        help="sync the project wiki (plus any extra wikis) and merge into ALL.md",
    )
    parser.add_argument(
        "-i",
        "--info",
        action="store_true",
        help="print the layout and remotes",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="list repositories under the scope with their current branch",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="fetch and fast-forward every repository (and wiki) under the scope",
    )

    sub = parser.add_subparsers(dest="command")
    worktree = sub.add_parser("worktree", help="manage worktrees")
    worktree.add_argument("-c", "--create", metavar="BRANCH", dest="branch")
    worktree.add_argument("-r", "--remove", metavar="BRANCH", dest="remove")
    return parser


def _is_url(value: str) -> bool:
    return value.startswith(("git@", "https://", "http://"))


def _scope(url: str | None) -> tuple[str, ...]:
    """Resolve a ``-u`` value to a scope for bulk operations."""
    if url is None:
        return ()
    if _is_url(url):
        raise GatherError(f"expected a path prefix, not a url: {url!r}")
    return parse_scope(url)


def resolve_remote(root: Path, url: str) -> Remote:
    """Resolve a full url to a :class:`Remote`, or a ``host/owner/repo`` path to
    the remote of an already-setup checkout."""
    if _is_url(url):
        return Remote.parse(url)
    parts = parse_scope(url)
    if len(parts) != 3:
        raise GatherError(f"expected <host>/<owner>/<repo>, got {url!r}")
    path = root.joinpath(*parts)
    if not (path / ".git").exists():
        raise GatherError(
            f"repository {path} does not exist; run --setup with a full url first"
        )
    return Remote.from_path(path)


def _cmd_list(layout: Layout, url: str | None) -> None:
    for path in discover(layout, _scope(url)):
        if path.name.endswith(".wiki"):
            continue
        print(f"{path.relative_to(layout.root)}  {current_branch(path)}")


def _cmd_sync(layout: Layout, url: str | None) -> None:
    for path in discover(layout, _scope(url)):
        print(f"syncing {path.relative_to(layout.root)}")
        try:
            sync_existing(path)
        except (NoRemoteError, ForbiddenError):
            print("no remote or forbidden")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(_PROJECTS_DIR).expanduser()
    layout = Layout(root)

    try:
        if args.list:
            _cmd_list(layout, args.url)
            return 0
        if args.sync:
            _cmd_sync(layout, args.url)
            return 0

        if args.url is None:
            parser.error("--url is required (or use --list / --sync)")

        if args.setup:
            if not _is_url(args.url):
                parser.error(f"--setup requires a full url, got {args.url!r}")
            remote = Remote.parse(args.url)
            print(f"reference repository is at {Manager(layout, remote).setup()}")
            return 0

        remote = resolve_remote(root, args.url)
        manager = Manager(layout, remote)

        if args.wiki is not None:
            print(f"all wiki pages are at {sync_wikis(layout, remote, args.wiki)}")

        if args.info:
            manager.info()

        if args.command == "worktree":
            if args.branch:
                print(f"worktree repository is at {manager.worktree_add(args.branch)}")
            elif args.remove:
                manager.worktree_remove(args.remove)
                print("worktree removed")

        return 0
    except GatherError as exc:
        print(f"gather: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
