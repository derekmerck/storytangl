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


def test_group_fragment_names_itself_without_its_members() -> None:
    """A group is a relational overlay: it draws its own identity, not its
    contents, because the members are peer fragments that render themselves."""

    group = {
        "fragment_type": "group",
        "group_type": "zone",
        "zone_role": "packet",
        "member_ids": ["4ea790cc", "63573cb3"],
        "hints": {"label_text": "Credentials packet"},
    }

    assert _plain_fragment_lines(group) == ["[Credentials packet]"]


def test_empty_zone_still_appears() -> None:
    """A targetable zone with nothing in it is something the reader can act on.
    Drawing nothing would delete it from the story entirely."""

    empty = {
        "fragment_type": "group",
        "group_type": "zone",
        "zone_role": "packet",
        "member_ids": [],
        "hints": {"label_text": "Credentials packet"},
    }

    assert _plain_fragment_lines(empty) == ["[Credentials packet] (empty)"]


def test_unlabelled_group_falls_back_to_its_role() -> None:
    assert _plain_fragment_lines(
        {"fragment_type": "group", "group_type": "zone", "member_ids": []}
    ) == ["[zone] (empty)"]


def test_group_internals_never_reach_the_transcript() -> None:
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
    assert "[packet]" in lines
    assert not any("member_ids" in line for line in lines)
    assert not any("4ea790cc" in line for line in lines)


def test_unknown_fragment_survives_as_a_placeholder() -> None:
    """Extension fragments round-trip through ``fragment_from_dto`` so an
    unknown one reaches the client. Dropping it silently loses content the
    fragment-stream contract promises to carry."""

    fragment = {
        "fragment_type": "unknown",
        "content": {"kind": "mystery", "label_text": "Future widget"},
    }

    assert _plain_fragment_lines(fragment) == ["[unsupported mystery] Future widget"]


def test_unknown_fragment_placeholder_never_dumps_the_payload() -> None:
    fragment = {
        "fragment_type": "unknown",
        "content": {"kind": "mystery", "uid": "x", "member_ids": [1, 2], "secret": "hunter2"},
    }

    (line,) = _plain_fragment_lines(fragment)

    assert line == "[unsupported mystery]"
    for leak in ("member_ids", "hunter2", "uid"):
        assert leak not in line


def test_non_string_content_yields_no_text_rather_than_a_repr() -> None:
    fragment = {"fragment_type": "content", "content": {"uid": "x", "member_ids": [1, 2]}}

    assert _fragment_text(fragment) == ""
    assert not any("member_ids" in line for line in _plain_fragment_lines(fragment))


def test_content_fragment_with_no_text_stays_quiet() -> None:
    """The placeholder is for payloads we failed to render, not for a fragment
    that legitimately carries nothing."""

    assert _plain_fragment_lines({"fragment_type": "content", "content": ""}) == []


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


def _choice_lines(choice: object) -> list[str]:
    renderer = PlainTerminalRenderer()
    scene = SimpleNamespace(fragment_type="content", content="At the harbour.")
    return [
        str(line)
        for line in renderer.story_update(fragments=[scene], choices=[choice])
    ]


def test_a_replacing_blocker_becomes_the_refused_row() -> None:
    """A whole sentence stands in for the offer instead of annotating it.

    Without the flag the row reads the offer, then a code, then a paraphrase
    of the offer -- three accounts of one refusal, and at any width the reader
    loses the end of it.
    """

    choice = SimpleNamespace(
        text="Mira will trade a fish-shaped pen for a brass doorknob",
        available=False,
        unavailable_reason="not_holding",
        blockers=[
            SimpleNamespace(
                code="not_holding",
                message="Mira would take a brass doorknob, but you don't have one.",
                replaces_text=True,
            )
        ],
    )

    (line,) = [row for row in _choice_lines(choice) if row.startswith("x)")]

    assert line == "x) Mira would take a brass doorknob, but you don't have one."


def test_an_annotating_blocker_still_reads_beside_the_choice() -> None:
    """The default is unchanged: most refusals are clauses, not sentences."""

    choice = SimpleNamespace(
        text="Cross the bridge",
        available=False,
        unavailable_reason="missing_dependency",
        blockers=[
            SimpleNamespace(
                code="missing_dependency",
                message="The bridge is out.",
                replaces_text=False,
            )
        ],
    )

    (line,) = [row for row in _choice_lines(choice) if row.startswith("x)")]

    assert line == "x) Cross the bridge [locked: missing_dependency] [blockers: The bridge is out.]"
