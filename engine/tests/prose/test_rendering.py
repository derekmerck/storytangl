from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import jinja2
import pytest
from jinja2.ext import Extension

from tangl.prose import DialogHandler, MuBlock, RecursiveRenderError, TextRenderSession, render_text


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


@pytest.mark.parametrize("content", ["", "Plain text.", "  {single_braces} \n", "\n  literal\n"])
@pytest.mark.parametrize("preserve", [False, True])
@pytest.mark.parametrize("custom", [False, True])
def test_literal_session_skips_namespace_and_compilation(
    content: str, preserve: bool, custom: bool, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _Ctx({})
    environment = jinja2.Environment(
        variable_start_string="[[", variable_end_string="]]", keep_trailing_newline=True,
    ) if custom else jinja2.Environment(keep_trailing_newline=True)
    session = TextRenderSession(ctx=ctx, environment=environment)

    def forbidden(*_args: object, **_kw: object) -> None:
        pytest.fail("Literal rendering must not gather or compile")

    monkeypatch.setattr(ctx, "get_ns", forbidden)
    monkeypatch.setattr(environment, "from_string", forbidden)
    assert session.render(content, preserve_whitespace=preserve) == (
        content if preserve else content.strip()
    )


@pytest.mark.parametrize("content, expected", [
    ("{{ name }}", "Mina"),
    ("{% if name %}Hello{% endif %}", "Hello"),
    ("{# comment #}Hello", "Hello"),
])
@pytest.mark.parametrize("custom", [False, True])
def test_template_delimiters_still_gather_and_compile_once(
    content: str, expected: str, custom: bool, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _Ctx({"name": "Mina"})
    session = TextRenderSession(ctx=ctx)
    if custom:
        session.environment = jinja2.Environment(
            variable_start_string="[[", variable_end_string="]]",
            block_start_string="<%", block_end_string="%>",
            comment_start_string="<#", comment_end_string="#>",
        )
        for old, new in [("{{", "[["), ("}}", "]]"), ("{%", "<%"),
                         ("%}", "%>"), ("{#", "<#"), ("#}", "#>")]:
            content = content.replace(old, new)
    calls = {"gather": 0, "compile": 0}
    gather, compile_ = ctx.get_ns, session.environment.from_string

    def get_ns(source: object) -> dict[str, object]:
        calls["gather"] += 1
        return gather(source)

    def from_string(*args: object, **kw: object) -> jinja2.Template:
        calls["compile"] += 1
        return compile_(*args, **kw)

    monkeypatch.setattr(ctx, "get_ns", get_ns)
    monkeypatch.setattr(session.environment, "from_string", from_string)
    assert session.render(content) == expected
    assert calls == {"gather": 1, "compile": 1}


def test_custom_delimiters_can_make_default_variable_braces_literal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _Ctx({})
    session = TextRenderSession(ctx=ctx, environment=jinja2.Environment(
        variable_start_string="[[", variable_end_string="]]",
    ))

    def forbidden(*_args: object, **_kw: object) -> None:
        pytest.fail("Default variable braces are literal under this environment")

    monkeypatch.setattr(ctx, "get_ns", forbidden)
    monkeypatch.setattr(session.environment, "from_string", forbidden)
    assert session.render("{{ missing }}") == "{{ missing }}"


class _LiteralPreprocessor(Extension):
    def preprocess(self, source: str, name: str | None, filename: str | None = None) -> str:
        return "Prefix: " + source


def test_environment_preprocessing_is_not_bypassed_for_literals() -> None:
    session = TextRenderSession(ctx=_Ctx({}), environment=jinja2.Environment(
        extensions=[_LiteralPreprocessor],
    ))
    assert session.render("Hello") == "Prefix: Hello"


@pytest.mark.parametrize("max_depth", [0, -1])
def test_literal_input_preserves_nonpositive_depth_limit(max_depth: int) -> None:
    session = TextRenderSession(ctx=_Ctx({}), max_depth=max_depth)
    with pytest.raises(RecursiveRenderError, match="maximum depth"):
        session.render("Literal")


def test_literal_child_preserves_active_recursive_depth_limit() -> None:
    session = TextRenderSession(ctx=_Ctx({}), max_depth=1)
    with pytest.raises(RecursiveRenderError, match="maximum depth"):
        session.render("{{ render_child('literal', subject) }}", subject=_Child("Mina"))


@pytest.mark.parametrize("options, content, expected", [
    ({"line_statement_prefix": "%"}, "% set name = 'Mina'\nHello", "Hello"),
    ({"line_comment_prefix": "##"}, "## hidden\nHello", "\nHello"),
    ({}, "Hello\n", "Hello"),
    ({"keep_trailing_newline": True}, "Hello\r\n", "Hello\n"),
    ({"keep_trailing_newline": True, "newline_sequence": "\r\n"}, "Hello\n", "Hello\r\n"),
])
def test_environment_line_and_newline_rules_decline_literal_shortcut(
    options: dict[str, str | bool], content: str, expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _Ctx({})
    session = TextRenderSession(ctx=ctx, environment=jinja2.Environment(**options))
    calls: list[object] = []
    gather = ctx.get_ns

    def get_ns(source: object) -> dict[str, object]:
        calls.append(source)
        return gather(source)

    monkeypatch.setattr(ctx, "get_ns", get_ns)
    assert session.render(content, preserve_whitespace=True) == expected
    assert calls == [ctx.cursor]


@pytest.mark.parametrize("text, expected", [
    ("the blonde girl", "The blonde girl"),
    ("Rin and Nanae", "Rin and Nanae"),
    ("the NASA lab", "The NASA lab"),
    ("", ""),
    (" rin and NASA  ", " rin and NASA  "),
    ("\nrin and NASA", "\nrin and NASA"),
])
def test_upper_first_is_shared_by_ordinary_and_explicit_mu_block_templates(
    text: str, expected: str,
) -> None:
    ns = {"phrase": text}
    ctx = _Ctx(ns)
    template = "{{ phrase | upper_first }}"
    session = TextRenderSession(ctx=ctx)
    assert session.render(template, preserve_whitespace=True) == expected
    assert DialogHandler.render([MuBlock(template=template)], ctx=ctx, ns=ns)[0].content == expected
    assert session.render("{{ phrase }}", preserve_whitespace=True) == text


def test_upper_first_does_not_replace_capitalize_or_change_template_passes() -> None:
    ns = {"phrase": "Rin and Nanae", "generated": "{{ phrase }}"}
    ctx = _Ctx(ns)
    session = TextRenderSession(ctx=ctx)
    assert session.render("{{ phrase | capitalize }}") == "Rin and nanae"
    assert session.render("{{ generated | upper_first }}") == "Rin and Nanae"
    assert DialogHandler.render(
        [MuBlock(template="{{ generated | upper_first }}")], ctx=ctx, ns=ns,
    )[0].content == "{{ phrase }}"


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
