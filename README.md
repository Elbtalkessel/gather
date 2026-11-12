# gather

`gather` bootstraps a git repository, its wiki, and isolated worktrees into one
opinionated, host-namespaced layout. It is the single entry point an agent (or a
human) runs before doing any work on a repo.

```sh
gather -u git@gitea.x.home.arpa:python/gather.git -s    # clone the reference
gather -u python/gather -w git@gitea.x.home.arpa:kb/gitea.git   # sync wikis
gather -u python/gather worktree -c feature/thing       # create a worktree
```

## Why

On a self-hosted forge, every agent that touches a repo re-derives the same
three things by hand: where the checkout lives, how to pull the knowledge
(wikis), and where to put an isolated workspace. `gather` makes those decisions
once and enforces them everywhere:

- **One reference clone, read-only.** It stays on the default branch and is
  never edited. All work happens in a worktree, so concurrent agents share one
  object store instead of duplicating it.
- **The wiki is a first-class repository**, pulled with the same machinery as
  the repo, not a special case. Knowledge lives in the wiki, never scattered
  through the checkout.
- **Isolated worktrees.** One branch per change; a branch created or pushed in
  one worktree is immediately visible to the others.

## Layout

Under `$XDG_PROJECTS_DIR` (default `~/Projects`), paths are namespaced by host:

```
~/Projects/
  gitea.x.home.arpa/
    python/
      gather              # reference clone
      gather.wiki         # wiki (first-class sibling)
  worktrees/
    gitea.x.home.arpa/
      python/
        gather/
          feature/x       # worktrees
  .gather/                # derived artifacts (merged ALL.md)
```

The full remote address is the path: `git@gitea.x.home.arpa:python/gather.git`
lives at `gitea.x.home.arpa/python/gather`.

## Commands

- `-u, --url <url>` — a full git url or a `host/owner/repo` path. `--setup`
  accepts either: an existing checkout is updated, a missing one is cloned via
  https.
- `-s, --setup` — clone or update the reference repository.
- `-w, --wiki [extra-url ...]` — sync the project wiki (plus any extra wikis,
  e.g. the instance wiki) and merge every page into one `ALL.md` for
  drift-finding. Each page is prefixed with `----` and a `source:` line.
- `-i, --info` — print the resolved paths and remotes.
- `worktree -c <branch>` — create a worktree. It fetches first, tracks
  `origin/<branch>` when that remote branch exists (a PR branch, say), and syncs
  an existing worktree to the remote head instead of returning it stale.
- `worktree -r <branch>` — remove a worktree.

## Development

```sh
devenv shell      # provides python + uv + ruff + ty
uv sync           # install the project and its dev group (pytest)
pytest            # run the tests
ruff check .      # lint
ty check          # type check
```
