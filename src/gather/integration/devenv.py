from pathlib import Path

from gather.processes import Process


class Devenv:
    root: Path

    def __init__(self, root: Path) -> None:
        self.root = root

    def setup(self) -> None:
        Process("devenv shell -- echo 'devenv ready'", cwd=self.root).try_run()

    def is_available(self) -> bool:
        return (self.root / "devenv.nix").exists()
