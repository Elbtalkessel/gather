import socket
from pathlib import Path

from gather.integration import Devenv, Git
from gather.processes import Process


class Manager:
    root: Path
    _worktrees: Path
    _wikis: Path
    git: Git

    def __init__(self, root: Path, url: str):
        self.root = root
        self._worktrees = self.root / "worktrees"
        self._wikis = self.root / "wikis"
        self.git = (
            Git(url) if url.startswith(("git", "http")) else Git.from_path(root / url)
        )

        self.root.mkdir(exist_ok=True)
        self._worktrees.mkdir(exist_ok=True)
        self._wikis.mkdir(exist_ok=True)

    @property
    def project(self) -> Path:
        return self.root / self.git.owner / self.git.repo

    @property
    def wiki(self) -> Path:
        return self._wikis / self.git.owner / self.git.repo

    @property
    def wiki_all(self) -> Path:
        return self.wiki / "ALL.md"

    @property
    def wiki_source(self) -> Path:
        return self.wiki / "source"

    @property
    def worktrees(self) -> Path:
        return self._worktrees / self.git.owner / self.git.repo

    def setup(self) -> Path:
        self.project.mkdir(parents=True, exist_ok=True)
        if not (self.project / ".git").exists():
            self.git.clone(self.project)
        else:
            self.git.pull(self.project)
        return self.project

    def wiki_sync(self) -> Path:
        self.wiki_source.mkdir(parents=True, exist_ok=True)
        self.git.wiki.ensure(self.wiki_source)
        return self.wiki_source

    def info(self):
        items = (
            ("Username", Process("git config --get user.name").try_run()),
            ("Email", Process("git config --get user.email").try_run()),
            ("Hostname", socket.gethostname()),
            ("Wiki", str(self.wiki_all)),
            ("Project", str(self.project)),
            ("Worktrees", str(self.worktrees)),
            ("Wiki Git", self.git.wiki.origin),
            ("Project Git", self.git.origin),
        )
        for name, value in items:
            print(f"{name}: {value}")

    def worktree_add(self, branch: str) -> Path:
        wt = self.git.worktree_add(self.project, self.worktrees, branch)
        devenv = Devenv(wt)
        if devenv.is_available():
            Devenv(wt).setup()
        return wt

    def worktree_remove(self, branch: str) -> None:
        self.git.worktree_remove(self.project, self.worktrees, branch)


def combine_wiki(managers: list[Manager], output: Path):
    if output.exists():
        output.unlink()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.touch()
    with open(output, "at") as f:
        for manager in managers:
            result = manager.wiki_sync()
            for page in result.glob("*.md"):
                f.write("----\n")
                f.write(f"source: {page.name} from {manager.git.wiki.origin}\n")
                f.write(page.read_text())
