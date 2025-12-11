from __future__ import annotations

from tangl.story.episode import Block
from tangl.story.story_graph import StoryGraph
from tangl.vm import Frame, ResolutionPhase as P


def test_block_renders_dialog_fragments(extract_fragments) -> None:
    graph = StoryGraph(label="dialog_story")
    block = Block(graph=graph, label="dialog", content="> [!POV] MC\n> I'm speaking.")

    frame = Frame(graph=graph, cursor_id=block.uid)
    fragments = frame.run_phase(P.JOURNAL)

    dialog_fragments = extract_fragments(fragments, "attributed")
    assert len(dialog_fragments) == 1
    dialog_fragment = dialog_fragments[0]

    assert dialog_fragment.who == "MC"
    assert dialog_fragment.how == "POV"
    assert dialog_fragment.content == "I'm speaking."
    assert not extract_fragments(fragments, "block")
