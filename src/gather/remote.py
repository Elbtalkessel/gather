"""A git remote, parsed into its host/owner/repo parts."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from gather.errors import GatherError
from gather.process import Process


@dataclass(frozen=True)
class Remote:
    """An immutable git remote.

    ``path`` is the on-disk directory the remote maps to under the projects
    root: ``<host>/<owner>/<repo>``.
    """

    host: str
    owner: str
    repo: str
    proto: str  # "ssh" | "https"

    @property
    def path(self) -> Path:
        return Path(self.host) / self.owner / self.repo

    @property
    def origin(self) -> str:
        if self.proto == "ssh":
            return f"git@{self.host}:{self.owner}/{self.repo}.git"
        return f"https://{self.host}/{self.owner}/{self.repo}.git"

    @property
    def wiki(self) -> Remote:
        """The sibling wiki remote (``<repo>.wiki``)."""
        return Remote(self.host, self.owner, f"{self.repo}.wiki", self.proto)

    @classmethod
    def parse(cls, url: str) -> Remote:
        url = url.strip()
        if url.startswith("git@"):
            return cls._parse_ssh(url)
        if url.startswith(("https://", "http://")):
            return cls._parse_https(url)
        return cls._parse_path(url)

    @staticmethod
    def _parse_path(value: str) -> Remote:
        """Parse a bare ``host/owner/repo`` path, defaulting to https."""
        parts = [part for part in value.strip("/").split("/") if part]
        if len(parts) != 3 or not all(parts):
            raise GatherError(f"expected <host>/<owner>/<repo>, got {value!r}")
        host, owner, repo = parts
        return Remote(host, owner, repo.removesuffix(".git"), "https")

    @classmethod
    def from_path(cls, path: Path) -> Remote:
        """Resolve a remote from an existing checkout's ``origin``."""
        origin = Process(
            "git", "-C", str(path), "remote", "get-url", "origin"
        ).checked().out
        return cls.parse(origin)

    @staticmethod
    def _parse_ssh(url: str) -> Remote:
        rest = url.removeprefix("git@")
        host, sep, rest = rest.partition(":")
        if not sep:
            raise GatherError(f"invalid ssh url, missing ':': {url!r}")
        owner, _, repo = rest.rstrip("/").partition("/")
        if not owner or not repo:
            raise GatherError(f"invalid ssh url: {url!r}")
        return Remote(host, owner, repo.removesuffix(".git"), "ssh")

    @staticmethod
    def _parse_https(url: str) -> Remote:
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        parts = parsed.path.strip("/").split("/")
        if host is None or len(parts) != 2 or not all(parts):
            raise GatherError(f"invalid https url: {url!r}")
        owner, repo = parts
        return Remote(host, owner, repo.removesuffix(".git"), "https")
