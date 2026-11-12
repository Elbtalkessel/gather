"""Git operations, concurrency-safe for a shared reference/wiki clone."""

from __future__ import annotations

from pathlib import Path

from gather.errors import DirtyReferenceError, ForbiddenError, NoRemoteError
from gather.process import Process, ProcessError
from gather.remote import Remote

_FORBIDDEN_MARKERS = (
    "permission denied",
    "authentication failed",
    "could not read from remote repository",
    "access rights",
    "could not read username",
)


def has_origin(path: Path) -> bool:
    """Return whether the checkout declares an ``origin`` remote."""
    return Process("git", "-C", str(path), "remote", "get-url", "origin").run().ok


def _is_forbidden(stderr: str) -> bool:
    lowered = stderr.lower()
    return any(marker in lowered for marker in _FORBIDDEN_MARKERS)


def sync_existing(path: Path) -> None:
    """Fetch and fast-forward an existing checkout.

    Fast-forward (rather than ``git pull --rebase``) is deliberate: ``git pull``
    races on its upstream resolution when several processes target the same clone
    concurrently. ``fetch`` + ``merge --ff-only`` is safe under concurrency and
    never rewrites local history — if the local branch has diverged it errors
    instead of silently rebasing.

    A checkout with no ``origin`` remote, or whose remote rejects access, is not
    syncable and raises a dedicated error so callers can skip it.

    An empty clone (a wiki with no pages yet, for example) has an unborn branch:
    ``HEAD`` names a branch that has no commits, so ``rev-parse`` cannot resolve
    it. It is fast-forwarded by adopting the remote tracking branch once that
    exists, and skipped entirely while both sides are still empty.
    """
    if not has_origin(path):
        raise NoRemoteError(f"{path} has no 'origin' remote")
    fetch = Process("git", "-C", str(path), "fetch", "origin").run()
    if not fetch.ok:
        if _is_forbidden(fetch.err):
            raise ForbiddenError(f"{path} remote rejected access")
        raise ProcessError(fetch)
    branch = Process(
        "git", "-C", str(path), "symbolic-ref", "--quiet", "--short", "HEAD"
    ).run().out
    if not branch:
        return  # detached HEAD: nothing to fast-forward
    remote_ref = f"origin/{branch}"
    if not Process(
        "git", "-C", str(path), "rev-parse", "--verify", "HEAD"
    ).run().ok:
        # Unborn branch (empty clone): adopt the remote branch if it now exists.
        if Process(
            "git", "-C", str(path), "rev-parse", "--verify", remote_ref
        ).run().ok:
            Process(
                "git", "-C", str(path), "checkout", "-B", branch, remote_ref
            ).checked()
        return
    Process("git", "-C", str(path), "merge", "--ff-only", remote_ref).checked()


def current_branch(path: Path) -> str:
    """Return the branch a checkout is on (``HEAD`` when detached)."""
    return Process(
        "git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"
    ).run().out


def default_branch(path: Path) -> str:
    """Return the remote default branch name (e.g. ``main``), or ``""`` if unknown.

    The default branch is whatever ``origin/HEAD`` points at — the branch the
    reference clone started on when it was cloned. An empty string means it
    could not be resolved (no ``origin`` remote, say), in which case callers
    should skip the branch check rather than guess.
    """
    ref = Process(
        "git", "-C", str(path), "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"
    ).run().out
    return ref.removeprefix("refs/remotes/origin/")


def ensure_clean(path: Path, *, force: bool = False) -> None:
    """Enforce the reference-clone invariant: clean and on the default branch.

    A clone off its default branch is checked out back to it — safe, since
    branch refs and commits are preserved and only the checked-out HEAD moves.
    A dirty working tree is refused (:class:`DirtyReferenceError`) because
    discarding it would destroy uncommitted work, unless ``force`` opts into
    the discard (``reset --hard`` + ``clean -fd``).
    """
    current = current_branch(path)
    default = default_branch(path)
    status = Process("git", "-C", str(path), "status", "--short").run().out
    if status and not force:
        hint = (
            current
            if current and current != "HEAD" and current != default
            else "<branch>"
        )
        raise DirtyReferenceError(
            f"{path} is dirty (uncommitted changes): the reference clone must "
            f"stay clean.\n"
            f"do all work in a worktree, not the reference clone:\n"
            f"  gather worktree -c {hint}\n"
            f"git status --short:\n{status}\n"
            "re-run with --force to discard these changes"
        )
    if force and status:
        Process("git", "-C", str(path), "reset", "--hard").checked()
        Process("git", "-C", str(path), "clean", "-fd").checked()
    if current and default and current != default:
        Process("git", "-C", str(path), "checkout", default).checked()


class Git:
    """Wrap the git commands gather needs against a single remote."""

    def __init__(self, remote: Remote) -> None:
        self.remote = remote

    def clone(self, path: Path) -> None:
        Process("git", "clone", self.remote.origin, str(path), timeout=60.0).checked()

    def sync(self, path: Path) -> None:
        """Clone if absent, else fetch and fast-forward."""
        path.parent.mkdir(parents=True, exist_ok=True)
        if (path / ".git").exists():
            sync_existing(path)
        else:
            self.clone(path)

    def worktree_add(self, repo: Path, root: Path, branch: str) -> Path:
        path = root / branch
        # Fetch so ``origin/<branch>`` reflects the remote head before a
        # worktree is added or an existing one is synced against it.
        Process("git", "-C", str(repo), "fetch", "origin").checked()
        remote_ref = f"origin/{branch}"
        has_remote = Process(
            "git", "-C", str(repo), "rev-parse", "--verify", remote_ref
        ).run().ok

        if path.exists():
            # An existing worktree is synced to the remote head instead of
            # being returned stale.
            if has_remote:
                Process(
                    "git", "-C", str(path), "reset", "--hard", remote_ref
                ).checked()
            return path

        if has_remote:
            # Track the existing remote branch (e.g. a PR branch) rather than
            # branching from the reference clone's HEAD.
            Process(
                "git", "-C", str(repo), "worktree", "add", str(path), branch
            ).checked()
        else:
            Process(
                "git", "-C", str(repo), "worktree", "add", str(path), "-b", branch
            ).checked()
        return path

    def worktree_remove(self, repo: Path, root: Path, branch: str) -> None:
        path = root / branch
        # Best-effort cleanup: report failures, don't raise.
        Process("git", "-C", str(repo), "worktree", "remove", str(path)).run()
        Process("git", "-C", str(repo), "branch", "-D", branch).run()
