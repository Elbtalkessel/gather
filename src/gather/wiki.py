"""Merging multiple wikis into a single drift-finding view."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from gather.remote import Remote


def merge_wikis(wikis: Sequence[tuple[Remote, Path]], output: Path) -> None:
    """Concatenate every wiki page into ``output``.

    Each page is preceded by::

        ----
        source: <Page>.md from <wiki origin>

    ``wikis`` is a list of ``(wiki_remote, wiki_path)`` pairs; the pages are
    appended in the given order, sorted by name within each wiki.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as fh:
        for remote, path in wikis:
            for page in sorted(path.glob("*.md")):
                fh.write("----\n")
                fh.write(f"source: {page.name} from {remote.origin}\n")
                fh.write(page.read_text())
