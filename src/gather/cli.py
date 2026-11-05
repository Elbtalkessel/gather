"""Command-line interface for gather."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from gather import ops
from gather.errors import GatherError
from gather.layout import Layout
from gather.manager import Manager, sync_wikis

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
            "full git url or a <host>/<owner>/<repo> path; --list/--sync also "
            "accept a scope prefix: <host> or <host>/<owner>"
        ),
    )
    parser.add_argument(
        "-s",
        "--setup",
        action="store_true",
        help="clone or update the reference repository (a bare path clones via https)",
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(_PROJECTS_DIR).expanduser()
    layout = Layout(root)

    try:
        if args.list:
            for entry in ops.list_repos(layout, args.url):
                print(f"{entry['path']}  {entry['branch']}")
            return 0
        if args.sync:
            for entry in ops.sync(layout, args.url):
                print(f"syncing {entry['path']}")
                if entry["status"] != "ok":
                    print(entry["status"])
            return 0

        if args.url is None:
            parser.error("--url is required (or use --list / --sync)")

        if args.setup:
            remote = ops.resolve_remote(root, args.url, allow_missing=True)
            print(f"reference repository is at {Manager(layout, remote).setup()}")
            return 0

        remote = ops.resolve_remote(root, args.url)
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
