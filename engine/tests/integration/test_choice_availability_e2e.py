import logging

from tangl.story.episode import Action, Block
from tangl.story.story_graph import StoryGraph
from tangl.vm import Frame, ResolutionPhase as P
from tangl.vm.provision import Dependency, ProvisioningPolicy, Requirement

from helpers.fragment_helpers import (
    count_fragments_by_type,
    extract_all_choices,
    extract_fragments,
)

def test_locked_choice_surfaces_to_journal() -> None:
    graph = StoryGraph(label="choice_availability")
    hallway = Block(graph=graph, label="hallway", content="You are in a hallway.")
    open_room = Block(graph=graph, label="open_room")
    locked_room = Block(graph=graph, label="locked_room")

    Action(
        graph=graph,
        source_id=hallway.uid,
        destination_id=open_room.uid,
        label="enter_open_room",
        content="Enter open room",
    )
    Action(
        graph=graph,
        source_id=hallway.uid,
        destination_id=locked_room.uid,
        label="enter_locked_room",
        content="Enter locked room",
        conditions=["False"],
    )

    key_requirement = Requirement(
        graph=graph,
        identifier="keycard",
        policy=ProvisioningPolicy.EXISTING,
        hard_requirement=True,
    )
    Dependency(graph=graph, source_id=locked_room.uid, requirement=key_requirement, label="keycard")

    graph.initial_cursor_id = hallway.uid

    frame = Frame(graph=graph, cursor_id=graph.initial_cursor_id)
    fragments = frame.run_phase(P.JOURNAL)

    logging.debug( fragments )
    counts = count_fragments_by_type(fragments)
    logging.debug(counts)

    content_fragments = extract_fragments(fragments, "content")
    assert content_fragments

    # grab choices from anywhere
    choice_fragments = extract_all_choices(fragments)
    assert len(choice_fragments) == 2
    assert count_fragments_by_type(fragments)["choice"] == 2

    # choice_fragments = [fragment for fragment in fragments if fragment.fragment_type == "choice"]
    assert len(choice_fragments) == 2

    active = [fragment for fragment in choice_fragments if fragment.active]
    locked = [fragment for fragment in choice_fragments if not fragment.active]

    assert len(active) == 1
    assert len(locked) == 1

    assert "open room" in active[0].content.lower()
    assert "locked room" in locked[0].content.lower()
    assert locked[0].unavailable_reason is not None
    assert "keycard" in locked[0].unavailable_reason.lower()
