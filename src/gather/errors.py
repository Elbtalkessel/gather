"""Exception hierarchy for gather."""

from __future__ import annotations


class GatherError(Exception):
    """Base class for every gather error."""


class NoRemoteError(GatherError):
    """The checkout has no ``origin`` remote."""


class ForbiddenError(GatherError):
    """The checkout's remote rejected the fetch (missing or invalid access)."""


class DirtyReferenceError(GatherError):
    """A reference clone has uncommitted changes and refused to discard them."""
