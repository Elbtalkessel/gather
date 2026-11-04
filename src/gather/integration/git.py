import re
import typing
from pathlib import Path

from gather.processes import Process

RE_URL = re.compile(
    r"((?P<proto>git@|https://)(?P<host>[\w\.@]+)(/|:))(?P<owner>[\w,\-,\_]+)/(?P<repo>[.\w,\-,\_]+)(.git){1}((/){0,1})"
)


class Git:
    proto: typing.Literal["git", "https"]
    host: str
    owner: str
    repo: str
    origin: str

    def __init__(self, url: str) -> None:
        m = RE_URL.search(url)
        assert m is not None, "invalid git url, git@.. or https:// only."
        self.proto = "git" if "git" in m.group("proto") else "https"
        self.host = m.group("host")
        self.owner = m.group("owner")
        self.repo = m.group("repo")
        self.origin = url

    @property
    def wiki(self) -> Git:
        return Git(url=self.origin.replace(".git", ".wiki.git"))

    def clone(self, path: Path) -> str:
        return Process("git", "clone", self.origin, str(path), timeout=60).try_run()

    def pull(self, path: Path) -> str:
        if not path.exists():
            raise ValueError(f"path {path} does not exist.")
        if not (path / ".git").exists():
            raise ValueError(f"path {path} is not git managed.")
        return Process("git", "-C", str(path), "pull", "--rebase").try_run()

    def ensure(self, path: Path) -> str:
        if path.exists() and (path / ".git").exists():
            return self.pull(path)
        return self.clone(path)

    @classmethod
    def from_path(cls, path: Path) -> Git:
        result = Process(
            "git", "-C", str(path), "remote", "get-url", "origin"
        ).try_run()
        return cls(result)

    def worktree_add(self, repo: Path, wt: Path, name: str) -> Path:
        path = wt / name
        Process(
            "git", "-C", str(repo), "worktree", "add", str(path), "-b", name
        ).try_run()
        return path

    def worktree_remove(self, repo: Path, wt: Path, name: str) -> None:
        path = wt / name
        r = Process("git", "-C", str(repo), "worktree", "remove", str(path)).run()
        if r.code != 0:
            print(r.err)
        r = Process("git", "-C", str(repo), "branch", "-D", name).run()
        if r.code != 0:
            print(r.err)
