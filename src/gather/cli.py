import argparse
import os
from pathlib import Path

from gather.manager import Manager, combine_wiki


def parse_args(root: Path) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-u",
        "--url",
        help="full url (required for running setup) or only <owner>/<repo>",
        type=str,
        metavar="REPOSITORY_URL",
        required=True,
    )
    parser.add_argument(
        "-s",
        "--setup",
        help="setup repository, requires full url",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-w",
        "--wiki",
        help="sync and merge wiki pages",
        type=str,
        nargs="*",
        metavar="EXTRA_REPO_URL",
    )
    parser.add_argument(
        "-i",
        "--info",
        help="show repository information",
        action="store_true",
        default=False,
    )

    sp = parser.add_subparsers(dest="cmd")

    wt = sp.add_parser("worktree")
    wt.add_argument(
        "-c",
        "--create",
        help="create a new worktree",
        type=str,
        default=argparse.SUPPRESS,
        metavar="BRANCH_NAME",
        dest="worktree_create",
    )
    wt.add_argument(
        "-r",
        "--remove",
        help="remove a worktree",
        type=str,
        default=argparse.SUPPRESS,
        metavar="BRANCH_NAME",
        dest="worktree_remove",
    )

    args = parser.parse_args()
    if args.setup and not args.url.startswith(("git", "http")):
        raise parser.error(
            f"--setup(-s) requires a full URL got '<owner>/<repo>' shorthand: {args.url!r}"
        )
    if not args.url.startswith(("git", "http")):
        target = root / args.url
        if not target.exists():
            raise parser.error(
                f"passed shorthand for --url(-u) but {target} doesn't exist, setup it first"
            )
        if not (target / ".git").exists():
            raise parser.error(f"directory {target} is not git managed")
    return args


def main():
    root = Path(os.getenv("XDG_PROJECTS_DIR") or "~/Projects").expanduser()
    args = parse_args(root)
    m = Manager(root, args.url)
    if args.setup:
        p = m.setup()
        print(f"reference repository is at {p}")
    if args.wiki is not None:
        combine_wiki([m] + [Manager(root, url) for url in args.wiki], m.wiki_all)
        print(f"all wiki pages are at {m.wiki_all}")
    if args.info:
        m.info()
    if args.cmd is None:
        return
    if args.cmd == "worktree":
        if b := getattr(args, "worktree_create", None):
            p = m.worktree_add(b)
            print(f"worktree repository is at {p}")
        if b := getattr(args, "worktree_remove", None):
            m.worktree_remove(b)
            print("worktree removed")


if __name__ == "__main__":
    main()
