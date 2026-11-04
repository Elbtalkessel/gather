"""Command-line interface for gather."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from gather.errors import GatherError
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
        required=True,
        metavar="REPOSITORY_URL",
        help=(
            "full git url (required for --setup) or the <host>/<owner>/<repo> "
            "path of an already-setup repository"
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

    sub = parser.add_subparsers(dest="command")
    worktree = sub.add_parser("worktree", help="manage worktrees")
    worktree.add_argument("-c", "--create", metavar="BRANCH", dest="branch")
    worktree.add_argument("-r", "--remove", metavar="BRANCH", dest="remove")
    return parser


def _is_url(value: str) -> bool:
    return value.startswith(("git@", "https://", "http://"))


def resolve_remote(root: Path, url: str) -> Remote:
    """Resolve a full url to a :class:`Remote`, or a host/owner/repo path to the
    remote of an already-setup checkout."""
    if _is_url(url):
        return Remote.parse(url)
    path = root / url
    if not path.exists():
        raise GatherError(
            f"repository {path} does not exist; run --setup with a full url first"
        )
    return Remote.from_path(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(_PROJECTS_DIR).expanduser()
    layout = Layout(root)

    try:
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
