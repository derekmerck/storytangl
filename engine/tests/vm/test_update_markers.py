"""Tests for update-cycle markers on the record stream."""

import pytest

from tangl.story.episode import Action, Block
from tangl.story.story_graph import StoryGraph
from tangl.vm import Frame, Ledger, ResolutionPhase as P


def test_update_marker_set_once_when_auto_following() -> None:
    """Ensure ``latest`` update markers are not duplicated by auto follows."""

    graph = StoryGraph(label="test")
    start = Block(graph=graph, label="start", content="start")
    mid = Block(graph=graph, label="mid", content="mid")
    end = Block(graph=graph, label="end", content="end")

    user_action = Action(
        graph=graph, source_id=start.uid, destination_id=mid.uid, label="to-mid"
    )
    Action(
        graph=graph,
        source_id=mid.uid,
        destination_id=end.uid,
        label="auto",
        trigger_phase=P.PREREQS,
    )

    ledger = Ledger(graph=graph, cursor_id=start.uid)
    frame = ledger.get_frame()

    initial_max = ledger.records.max_seq
    frame.resolve_choice(user_action)

    update_markers = ledger.records.markers.get("update", {})

    assert update_markers.get("latest") == initial_max + 1
    assert len(update_markers) == 1
