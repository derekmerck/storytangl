from __future__ import annotations

from tangl.core import StreamRegistry
from tangl.story.concepts import Concept
from tangl.story.episode.action import Action
from tangl.story.episode.block import Block
from tangl.story.story_graph import StoryGraph
from tangl.vm.ledger import Ledger


def test_block_journal_orders_block_concept_choice() -> None:
    story = StoryGraph(label="test_journal_order")
    start = story.add_node(obj_cls=Block, label="start", content="Start text")
    concept = story.add_node(obj_cls=Concept, label="glossary", content="Concept text")
    end = story.add_node(obj_cls=Block, label="end", content="End text")

    story.add_edge(start, concept)
    story.add_edge(start, end, obj_cls=Action, label="continue", content="Continue")

    story.initial_cursor_id = start.uid

    ledger = Ledger(
        graph=story,
        cursor_id=start.uid,
        records=StreamRegistry(),
        label="ledger",
    )
    ledger.init_cursor()

    fragments = [
        fragment
        for fragment in ledger.get_journal("step-0001")
        if getattr(fragment, "fragment_type", None) != "text"
    ]

    assert [fragment.fragment_type for fragment in fragments] == [
        "block",
        "concept",
        "choice",
    ]
    assert [fragment.content for fragment in fragments] == [
        "Start text",
        "Concept text",
        "Continue",
    ]
