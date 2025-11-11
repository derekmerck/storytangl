import pytest

from tangl.core import Graph
from tangl.vm import Frame, ResolutionPhase as P
from tangl.story.concepts.actor import Actor, Role
from tangl.story.episode import Scene, Block
from tangl.story.story_graph import StoryGraph

def test_structural_domain_vars_include_dependencies():
    g = StoryGraph()

    # todo: it doesn't provision ancestors when trying to provision the block
    # Create scene with role
    # scene = Scene(graph=g, label="throne")

    # Create block with req
    block = Block(
        graph=g,
        label="confront",
        content="{{antagonist.name}} rises menacingly."
    )

    role = Role(
        graph=g,
        source_id=block.uid,
        label="antagonist",
        actor_criteria={"archetype": "villain"}
    )

    class Actor_(Actor):
        archetype: str = "generic"

    # Create actor to be found
    villain = Actor_(graph=g, name="Dark Lord", archetype="villain")

    assert role.satisfied_by(villain)
    from tangl.vm.provision import Dependency, Affordance
    assert role in block.edges_out(is_instance=(Dependency, Affordance))

    # scene.add_member(block)

    # Run frame at block level
    frame = Frame(graph=g, cursor_id=block.uid)
    frame.run_phase(P.PLANNING)  # Should plan villain
    assert not role.satisfied

    frame.run_phase(P.FINALIZE)

    assert role.satisfied
    frame._invalidate_context()

    # print(frame.context.inspect_scope())


    # Get namespace at block level
    ns = frame.context.get_ns()

    # Should include scene's satisfied role
    assert 'antagonist' in ns
    assert ns['antagonist'] == villain

    # Journal should work with this namespace
    fragments = frame.run_phase(P.JOURNAL)
    prose = " ".join(f.content for f in fragments if hasattr(f, 'content'))
    assert "Dark Lord rises menacingly" in prose

