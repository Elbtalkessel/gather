"""Tests for Remote URL parsing and path derivation."""

from __future__ import annotations

from pathlib import Path

import pytest

from gather.errors import GatherError
from gather.remote import Remote


def test_parse_ssh() -> None:
    remote = Remote.parse("git@gitea.x.home.arpa:python/gather.git")
    assert remote.host == "gitea.x.home.arpa"
    assert remote.owner == "python"
    assert remote.repo == "gather"
    assert remote.proto == "ssh"


def test_parse_https() -> None:
    remote = Remote.parse("https://gitea.x.home.arpa/python/gather.git")
    assert remote.host == "gitea.x.home.arpa"
    assert remote.owner == "python"
    assert remote.repo == "gather"
    assert remote.proto == "https"


def test_parse_without_dot_git() -> None:
    remote = Remote.parse("git@gitea.x.home.arpa:python/gather")
    assert remote.repo == "gather"


def test_parse_repo_with_dot() -> None:
    remote = Remote.parse("git@gitea.x.home.arpa:python/gather.spike.git")
    assert remote.repo == "gather.spike"


def test_wiki_suffix() -> None:
    remote = Remote.parse("git@gitea.x.home.arpa:python/gather.git")
    assert remote.wiki.repo == "gather.wiki"
    assert remote.wiki.origin == "git@gitea.x.home.arpa:python/gather.wiki.git"


def test_path_is_host_namespaced() -> None:
    remote = Remote.parse("git@gitea.x.home.arpa:python/gather.git")
    assert remote.path == Path("gitea.x.home.arpa") / "python" / "gather"


def test_origin_roundtrip_ssh() -> None:
    remote = Remote.parse("git@gitea.x.home.arpa:python/gather.git")
    assert remote.origin == "git@gitea.x.home.arpa:python/gather.git"


def test_origin_roundtrip_https() -> None:
    remote = Remote.parse("https://gitea.x.home.arpa/python/gather.git")
    assert remote.origin == "https://gitea.x.home.arpa/python/gather.git"


def test_invalid_url() -> None:
    with pytest.raises(GatherError):
        Remote.parse("not-a-remote")
