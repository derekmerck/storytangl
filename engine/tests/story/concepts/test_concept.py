"""Tests for :mod:`tangl.story.reference_domain.concept`."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from tangl.core import BaseFragment, Graph, Node
from tangl.story.concepts import Concept
from tangl.vm import Frame, ResolutionPhase as P


def collect_fragment(fragments: Iterable[BaseFragment], *, source_id) -> BaseFragment:
    for fragment in fragments:
        print(fragment)
        if isinstance(fragment, BaseFragment) and getattr(fragment, "source_id", None) == source_id:
            return fragment
    raise AssertionError("Expected fragment from source was not produced")


class TestSimpleConcept:
    def test_stores_content(self):
        concept = Concept(label="test", content="Hello world")

        assert concept.content == "Hello world"
        assert concept.label == "test"

    def test_render_with_namespace(self):
        concept = Concept(label="greeting", content="Hello, {name}!")
        rendered = concept.render({"name": "Alice"})

        assert rendered == "Hello, Alice!"

    def test_render_without_variables(self):
        concept = Concept(label="plain", content="This is plain text.")

        rendered = concept.render({})
        assert rendered == "This is plain text."

    def test_render_missing_variables_returns_raw_content(self):
        concept = Concept(label="incomplete", content="Hello, {name}!")

        rendered = concept.render({})
        assert rendered == "Hello, {name}!"

    def test_journal_handler_emits_fragment(self):
        graph = Graph(label="test")
        concept = Concept(graph=graph, label="greeting", content="Welcome to the story.")

        frame = Frame(graph=graph, cursor_id=concept.uid)
        fragments = frame.run_phase(P.JOURNAL)
        fragment = collect_fragment(fragments, source_id=concept.uid)

        assert "Welcome to the story." in fragment.content
        assert fragment.source_id == concept.uid

    def test_render_uses_frame_namespace(self):
        graph = Graph(label="test")
        concept = Concept(graph=graph, locals={"player_name": "Bob"}, label="greeting", content="Hello, {player_name}!")

        frame = Frame(graph=graph, cursor_id=concept.uid)
        fragments = frame.run_phase(P.JOURNAL)
        fragment = collect_fragment(fragments, source_id=concept.uid)

        assert "Hello, Bob!" in fragment.content

    def test_handler_ignores_plain_nodes(self):
        graph = Graph(label="test")
        node = Node(graph=graph, label="plain")
        graph.add(node)

        frame = Frame(graph=graph, cursor_id=node.uid)
        fragments = frame.run_phase(P.JOURNAL)

        assert any("cursor" in fragment.content for fragment in fragments)
