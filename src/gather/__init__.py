"""gather — bootstrap git repos, their wikis, and worktrees in one opinionated layout."""

from __future__ import annotations

from gather.layout import Layout
from gather.manager import Manager
from gather.remote import Remote

__version__ = "0.1.0"

__all__ = ["Layout", "Manager", "Remote", "__version__"]
