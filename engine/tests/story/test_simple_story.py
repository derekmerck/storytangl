import logging
logging.basicConfig(level=logging.DEBUG)

from tangl.story.episode import Block
from tangl.story.story_graph import StoryGraph
from tangl.vm import ResolutionPhase as P

from tangl.story.episode import Scene
from tangl.story.concepts.location import Location, Setting
from tangl.story.concepts.actor import Actor, Role


def test_simple_story():
    g = StoryGraph()

    sc = Scene(graph=g, label="The next day")
    b = Block(graph=g, content="You arrive at {{ setting.name }} with {{ friend.name }}.")
    sc.add_member(b)

    sd = Setting(graph=g, label="setting", source_id=sc.uid)
    l = Location(graph=g, label="castle", name="the castle")
    sd.location = l

    rd = Role(graph=g, label="friend", source_id=sc.uid)
    a = Location(graph=g, label="alice", name="Alice the Adventurer")
    rd.actor = a

    from tangl.vm import Frame

    f = Frame(graph=g, cursor_id=b.uid)
    out = f.run_phase(P.JOURNAL)
    print([r.content for r in out])

    assert 'You arrive at the castle with Alice the Adventurer.' in [r.content for r in out]

    from pprint import pprint
    pprint([r.unstructure() for r in f.phase_receipts[P.JOURNAL]] )
