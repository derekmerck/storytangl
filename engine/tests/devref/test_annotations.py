from __future__ import annotations

from pathlib import Path

from tangl.devref.annotations import extract_storytangl_topic_annotations
from tangl.devref.builder import extract_symbol_refs, parse_sections


def test_extract_storytangl_topic_annotations_from_rst_and_myst() -> None:
    rst_text = """
.. storytangl-topic::
   :topics: entity, selector
   :facets: api, overview
   :relation: documents
"""
    myst_text = """
```{storytangl-topic}
:topics: ledger, frame
:facets: tests
:relation: tests
```
"""

    annotations = extract_storytangl_topic_annotations(rst_text + "\n" + myst_text)

    assert [item.topics for item in annotations] == [
        ["entity", "selector"],
        ["ledger", "frame"],
    ]
    assert annotations[0].facets == ["api", "overview"]
    assert annotations[1].relation == "tests"


def test_parse_sections_handles_markdown_and_rst() -> None:
    md_sections = parse_sections(
        Path("ARCHITECTURE.md"),
        "# Title\n\nbody\n\n## Entity\n\ndetails\n",
    )
    rst_sections = parse_sections(
        Path("identity.rst"),
        "Identity\n========\n\nbody\n\nLookup\n------\n\nmore\n",
    )

    assert [section.title for section in md_sections] == ["Title", "Entity"]
    assert [section.title for section in rst_sections] == ["Identity", "Lookup"]


def test_extract_symbol_refs_reads_autodoc_targets() -> None:
    text = """
.. autoclass:: tangl.core.Entity
.. autofunction:: tangl.story.analysis.project_story_graph
"""

    refs = extract_symbol_refs(text)

    assert refs == [
        "tangl.core.Entity",
        "tangl.story.analysis.project_story_graph",
    ]
