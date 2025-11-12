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


def test_block_journal_places_all_concepts_before_choices() -> None:
    story = StoryGraph(label="tavern_journal_order")
    tavern = story.add_node(
        obj_cls=Block,
        label="tavern",
        content="You enter the tavern.",
    )
    smell = story.add_node(
        obj_cls=Concept,
        label="smell",
        content="It smells of ale.",
    )
    sound = story.add_node(
        obj_cls=Concept,
        label="sound",
        content="Music plays softly.",
    )
    bar = story.add_node(obj_cls=Block, label="bar")
    corner = story.add_node(obj_cls=Block, label="corner")

    story.add_edge(tavern, smell)
    story.add_edge(tavern, sound)
    story.add_edge(
        tavern,
        bar,
        obj_cls=Action,
        label="Approach bar",
        content="Approach bar",
    )
    story.add_edge(
        tavern,
        corner,
        obj_cls=Action,
        label="Find corner",
        content="Find corner",
    )

    story.initial_cursor_id = tavern.uid

    ledger = Ledger(
        graph=story,
        cursor_id=tavern.uid,
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
        "concept",
        "choice",
        "choice",
    ]
    assert fragments[0].content == "You enter the tavern."
    assert {fragments[1].content, fragments[2].content} == {
        "It smells of ale.",
        "Music plays softly.",
    }
    assert [fragment.content for fragment in fragments[3:]] == [
        "Approach bar",
        "Find corner",
    ]
