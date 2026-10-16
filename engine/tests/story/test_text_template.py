"""Tests for the template language Story text is rendered in.

Organized by functionality:
- Declaration: fstring by default, jinja when a script's globals declare it,
  overridable per block, and an unknown language refused.
- Recursion: jinja renders again whatever template text a value produces.
- Jinja block text: whitespace kept, blocker messages in the block's language,
  authoring errors raised.
"""

from __future__ import annotations

from collections import ChainMap

import pytest
import jinja2

from tangl.core import Node
from tangl.journal.fragments import ChoiceFragment
from tangl.story import InitMode
from tangl.story.fabula.world import World
from tangl.story.system_handlers import _render_text
from tangl.vm import Ledger
from tangl.vm.runtime.frame import PhaseCtx


def _script(*, globals_: dict, content: str, block_locals: dict | None = None,
            actions: list[dict] | None = None, label: str = "text_template") -> dict:
    start: dict = {"content": content}
    if block_locals:
        start["locals"] = block_locals
    if actions:
        start["actions"] = actions
    return {
        "label": label,
        "metadata": {"title": "Text template", "start_at": "s.start"},
        "globals": {"name": "Mina", **globals_},
        "scenes": {"s": {"blocks": {"start": start, "later": {"content": "Later."}}}},
    }


def _output(script: dict) -> list:
    world = World.from_script_data(script_data=script)
    graph = world.create_story("text_template", init_mode=InitMode.EAGER).graph
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    frame = ledger.get_frame()
    frame.goto_node(ledger.cursor)
    return list(frame.output_stream)


def _rendered(script: dict) -> list[str]:
    return [r.content for r in _output(script) if isinstance(getattr(r, "content", None), str)]


# ============================================================================
# Declaration
# ============================================================================


class TestTextTemplateDeclaration:
    def test_fstring_is_the_default(self) -> None:
        assert "Hello Mina." in _rendered(_script(globals_={}, content="Hello {name}."))

    def test_jinja_when_the_script_declares_it(self) -> None:
        text = _rendered(_script(globals_={"text_template": "jinja"}, content="Hello {{ name }}."))
        assert "Hello Mina." in text

    def test_a_block_overrides_the_script(self) -> None:
        text = _rendered(_script(
            globals_={"text_template": "jinja"},
            content="Hello {name}.",
            block_locals={"text_template": "fstring"},
        ))
        assert "Hello Mina." in text

    def test_an_unknown_language_is_refused(self) -> None:
        with pytest.raises(ValueError):
            _rendered(_script(globals_={"text_template": "mustache"}, content="Hello."))

    def test_fstring_substitution_and_escaped_braces_are_unchanged(self) -> None:
        assert "Mina; {name}; {literal}" in _rendered(_script(
            globals_={}, content="{name}; {{name}}; {{literal}}",
        ))

    def test_single_braces_remain_literal_in_jinja(self) -> None:
        assert "{name}" in _rendered(_script(
            globals_={"text_template": "jinja"}, content="{name}",
        ))

    def test_literal_jinja_still_gathers_once_for_story_dialect_validation(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        world = World.from_script_data(script_data=_script(
            globals_={"text_template": "jinja"}, content="Hello.",
        ))
        graph = world.create_story("literal").graph
        ctx = PhaseCtx(graph=graph, cursor_id=graph.initial_cursor_id)
        calls: list[Node] = []
        gather = ctx.get_ns

        def get_ns(source: Node) -> ChainMap[str, object]:
            calls.append(source)
            return gather(source)

        def forbidden(*_args: object, **_kw: object) -> None:
            pytest.fail("Validated literal Jinja must not compile")

        monkeypatch.setattr(ctx, "get_ns", get_ns)
        monkeypatch.setattr(jinja2.Environment, "from_string", forbidden)
        assert _render_text("Hello.", source=ctx.cursor, ctx=ctx) == "Hello."
        assert calls == [ctx.cursor]


# ============================================================================
# Recursion
# ============================================================================


class TestJinjaRecursion:
    def test_template_text_a_value_produces_is_rendered_again(self) -> None:
        # `greeting` is itself a template; rendering `{{ greeting }}` yields it,
        # and the renderer keeps going until nothing is left to render.
        text = _rendered(_script(
            globals_={"text_template": "jinja", "greeting": "Hello {{ name }}"},
            content="{{ greeting }}!",
        ))
        assert "Hello Mina!" in text


# ============================================================================
# Jinja block text
# ============================================================================


class TestJinjaBlockText:
    def test_whitespace_is_kept_as_fstring_keeps_it(self) -> None:
        # Indentation makes a Markdown code block; the trailing newline is text.
        fstring = _rendered(_script(globals_={}, content="    {name}\n", label="as_fstring"))
        jinja = _rendered(_script(globals_={"text_template": "jinja"},
                                  content="    {{ name }}\n", label="as_jinja"))
        assert "    Mina\n" in fstring
        assert jinja == fstring

    def test_a_blocker_message_follows_its_block_s_language(self) -> None:
        output = _output(_script(
            globals_={},
            content="Start.",
            block_locals={"text_template": "jinja"},
            actions=[{
                "text": "Go on",
                "successor": "later",
                "conditions": ["False"],
                "blockers": [{"code": "not_yet", "message": "Ask {{ name }} first."}],
            }],
        ))
        [choice] = [r for r in output if isinstance(r, ChoiceFragment)]
        assert choice.blockers[0].message == "Ask Mina first."

    def test_an_authoring_error_is_raised_with_its_source(self) -> None:
        def broken() -> str:
            raise RuntimeError("no such outfit")

        with pytest.raises(RuntimeError, match="no such outfit") as raised:
            _rendered(_script(globals_={"text_template": "jinja", "broken": broken},
                              content="{{ broken() }}"))
        assert any("while rendering jinja text" in note for note in raised.value.__notes__)

