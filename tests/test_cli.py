"""Tests for CLI resolution and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from gather.cli import resolve_remote
from gather.errors import GatherError


def test_resolve_remote_rejects_non_leaf(tmp_path: Path) -> None:
    (tmp_path / "gitea.x.home.arpa").mkdir()
    with pytest.raises(GatherError):
        resolve_remote(tmp_path, "gitea.x.home.arpa")


def test_resolve_remote_rejects_missing_repo(tmp_path: Path) -> None:
    with pytest.raises(GatherError):
        resolve_remote(tmp_path, "gitea.x.home.arpa/python/gather")
