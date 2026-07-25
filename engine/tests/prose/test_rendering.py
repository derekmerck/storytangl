from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from tangl.prose import RecursiveRenderError, TextRenderSession, render_text


class _Ctx:
    cursor = SimpleNamespace(label="cursor")

    def __init__(self, namespace: dict[str, object]) -> None:
        self.namespace = namespace

    def get_ns(self, _source: object | None = None) -> dict[str, object]:
        return self.namespace


@dataclass
class _Child:
    name: str
    content: str = "{{ subject.name }}"


def test_render_text_returns_literal_text() -> None:
    assert render_text("A quiet room.", ctx=_Ctx({})) == "A quiet room."


def test_render_text_uses_gathered_namespace() -> None:
    assert render_text("Hello, {{ name }}.", ctx=_Ctx({"name": "Mina"})) == "Hello, Mina."


def test_render_text_follows_generated_template() -> None:
    assert (
        render_text(
            "{{ first }}",
            ctx=_Ctx({"first": "{{ second }}", "second": "Done"}),
        )
        == "Done"
    )


def test_render_child_keeps_its_subject_binding_inside_a_loop() -> None:
    children = [_Child("Ada"), _Child("Bea")]
    session = TextRenderSession(ctx=_Ctx({"children": children}))

    rendered = session.render(
        "{% for child in children %}[{{ render_child(child.content, child) }}]{% endfor %}",
    )

    assert rendered == "[Ada][Bea]"


def test_consecutive_segments_share_ephemeral_discourse() -> None:
    session = TextRenderSession(ctx=_Ctx({}))

    rendered = session.render_segments(
        [
            "{{ discourse.update({'focus': 'Mina'}) or '' }}",
            "{{ discourse.focus }} arrives.",
        ],
    )

    assert rendered == ["", "Mina arrives."]


def test_recursive_template_cycle_fails_clearly() -> None:
    with pytest.raises(RecursiveRenderError, match="cycle"):
        render_text(
            "{{ first }}",
            ctx=_Ctx({"first": "{{ second }}", "second": "{{ first }}"}),
        )


def test_repeated_recursive_output_fails_clearly() -> None:
    with pytest.raises(RecursiveRenderError, match="repeated output"):
        render_text(
            "{{ first }}",
            ctx=_Ctx({"first": "{{ same }}", "same": "{{ same }}"}),
        )


def test_recursive_template_honors_maximum_depth() -> None:
    session = TextRenderSession(
        ctx=_Ctx({"first": "{{ second }}", "second": "{{ third }}", "third": "Done"}),
        max_depth=2,
    )

    with pytest.raises(RecursiveRenderError, match="maximum depth"):
        session.render("{{ first }}")
