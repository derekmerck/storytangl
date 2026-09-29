"""Tests for the template language Story text is rendered in.

Organized by functionality:
- Declaration: fstring by default, jinja when a script's globals declare it,
  overridable per block, and an unknown language refused.
- Recursion: jinja renders again whatever template text a value produces.
"""

from __future__ import annotations

import pytest

from tangl.story import InitMode
from tangl.story.fabula.world import World
from tangl.vm import Ledger


def _script(*, globals_: dict, content: str, block_locals: dict | None = None) -> dict:
    start: dict = {"content": content}
    if block_locals:
        start["locals"] = block_locals
    return {
        "label": "text_template",
        "metadata": {"title": "Text template", "start_at": "s.start"},
        "globals": {"name": "Mina", **globals_},
        "scenes": {"s": {"blocks": {"start": start}}},
    }


def _rendered(script: dict) -> list[str]:
    world = World.from_script_data(script_data=script)
    graph = world.create_story("text_template", init_mode=InitMode.EAGER).graph
    ledger = Ledger.from_graph(graph, entry_id=graph.initial_cursor_id)
    frame = ledger.get_frame()
    frame.goto_node(ledger.cursor)
    return [r.content for r in frame.output_stream if isinstance(getattr(r, "content", None), str)]


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
