"""Tests for the wiki merge."""

from __future__ import annotations

from pathlib import Path

from gather.remote import Remote
from gather.wiki import merge_wikis

WIKI = Remote.parse("git@gitea.x.home.arpa:python/gather.git").wiki
WIKI_ORIGIN = "git@gitea.x.home.arpa:python/gather.wiki.git"


def test_merge_wikis_header_format(tmp_path: Path) -> None:
    wiki_dir = tmp_path / "gather.wiki"
    wiki_dir.mkdir()
    (wiki_dir / "Home.md").write_text("# Home\n")
    (wiki_dir / "Workflow.md").write_text("# Workflow\n")

    output = tmp_path / "ALL.md"
    merge_wikis([(WIKI, wiki_dir)], output)

    text = output.read_text()
    assert text.startswith(
        f"----\nsource: Home.md from {WIKI_ORIGIN}\n# Home\n"
    )
    assert f"source: Workflow.md from {WIKI_ORIGIN}\n# Workflow\n" in text


def test_merge_wikis_preserves_order(tmp_path: Path) -> None:
    first = tmp_path / "a"
    second = tmp_path / "b"
    first.mkdir()
    second.mkdir()
    (first / "P.md").write_text("first")
    (second / "Q.md").write_text("second")

    output = tmp_path / "ALL.md"
    merge_wikis([(WIKI, first), (WIKI, second)], output)

    assert output.read_text().index("first") < output.read_text().index("second")
