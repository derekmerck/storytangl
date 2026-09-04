"""Plain-renderer regression tests: no object repr may reach the transcript.

Two worlds used to dump internals into narrative prose -- ``repartee_loop``
spliced a media resource repr into its media line, and ``hall_monitor`` printed
a whole group fragment as a dict. Both surfaced through the plain renderer,
which is the text floor every other port degrades to.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from tangl.cli.rendering import (
    PlainTerminalRenderer,
    _fragment_text,
    _plain_fragment_lines,
)


def _transcript(fragments: list[object]) -> list[str]:
    renderer = PlainTerminalRenderer()
    return [str(line) for line in renderer.story_update(fragments=fragments, choices=[])]


def test_group_fragment_draws_nothing() -> None:
    """A group is a relational overlay; its members render on their own."""

    group = {
        "fragment_type": "group",
        "group_type": "zone",
        "zone_role": "packet",
        "member_ids": ["4ea790cc", "63573cb3"],
        "hints": {"label_text": "Credentials packet"},
    }

    assert _plain_fragment_lines(group) == []


def test_group_fragment_does_not_reach_the_transcript() -> None:
    lines = _transcript(
        [
            {"fragment_type": "piece", "piece_id": "candidate-0", "content": "Tess Alder"},
            {
                "fragment_type": "group",
                "group_type": "zone",
                "member_ids": ["4ea790cc"],
                "zone_role": "packet",
            },
        ]
    )

    assert "[candidate-0] Tess Alder" in lines
    assert not any("member_ids" in line for line in lines)
    assert not any("zone_role" in line for line in lines)


def test_non_string_content_yields_no_text_rather_than_a_repr() -> None:
    fragment = {"fragment_type": "content", "content": {"uid": "x", "member_ids": [1, 2]}}

    assert _fragment_text(fragment) == ""
    assert _plain_fragment_lines(fragment) == []


def test_media_fragment_names_the_resource() -> None:
    fragment = {
        "fragment_type": "media",
        "media_role": "narrative_im",
        "content": "quai_bg.png",
    }

    assert _plain_fragment_lines(fragment) == ["[narrative_im: quai_bg.png]"]


def test_media_object_content_is_named_from_its_label() -> None:
    rit = SimpleNamespace(label="quai_bg.png", path=Path("/w/media/images/quai_bg.png"))
    fragment = SimpleNamespace(
        fragment_type="media", media_role="narrative_im", content=rit
    )

    assert _plain_fragment_lines(fragment) == ["[narrative_im: quai_bg.png]"]


def test_media_object_repr_is_never_spliced_into_the_line() -> None:
    """Regression for the ``repartee_loop`` leak.

    ``label``/``path`` that are neither strings nor paths used to be run
    through ``str()`` and cut at the last path separator, pasting the tail of
    an object repr into the narrative.
    """

    opaque = SimpleNamespace(label=object(), path=object())
    fragment = SimpleNamespace(
        fragment_type="media", media_role="narrative_im", content=opaque
    )

    (line,) = _plain_fragment_lines(fragment)

    assert "object at 0x" not in line
    assert "SimpleNamespace" not in line
