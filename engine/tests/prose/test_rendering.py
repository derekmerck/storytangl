from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import jinja2
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


@dataclass
class _TreeSubject:
    name: str
    child: _TreeSubject | None = None
    content: str = (
        "{{ subject.name }}"
        "{% if subject.child %} {{ render_child(subject.content, subject.child) }}{% endif %}"
    )


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


def test_render_child_shares_recursive_cycle_protection() -> None:
    child = _Child("Ada", content="{{ render_child(subject.content, subject) }}")
    session = TextRenderSession(ctx=_Ctx({}))

    with pytest.raises(RecursiveRenderError, match="cycle"):
        session.render("{{ render_child(subject.content, subject) }}", subject=child)


def test_render_child_allows_one_template_for_distinct_tree_subjects() -> None:
    three = _TreeSubject("three")
    two = _TreeSubject("two", child=three)
    one = _TreeSubject("one", child=two)
    session = TextRenderSession(ctx=_Ctx({}))

    rendered = session.render(
        "{{ render_child(subject.content, subject) }}",
        subject=one,
    )

    assert rendered == "one two three"


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


def test_render_text_strips_generated_jinja_comments() -> None:
    assert render_text("{{ first }}", ctx=_Ctx({"first": "{# hidden #}Done"})) == "Done"


def test_render_text_honors_custom_environment_delimiters() -> None:
    session = TextRenderSession(
        ctx=_Ctx({"first": "[[ second ]]", "second": "Done"}),
        environment=jinja2.Environment(
            variable_start_string="[[",
            variable_end_string="]]",
        ),
    )

    assert session.render("[[ first ]]") == "Done"


def test_render_text_raises_for_undefined_symbols_by_default() -> None:
    with pytest.raises(jinja2.UndefinedError):
        render_text("A {{ missing }} arrives.", ctx=_Ctx({}))


def test_render_text_accepts_an_explicit_permissive_environment() -> None:
    session = TextRenderSession(ctx=_Ctx({}), environment=jinja2.Environment())

    assert session.render("A {{ missing }} arrives.") == "A  arrives."
