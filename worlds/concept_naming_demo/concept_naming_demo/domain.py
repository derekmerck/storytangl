"""Adopt naming vocabulary before world compilation."""
from __future__ import annotations

from tangl.core import BehaviorRegistry, EntityTemplate, Node, Selector
from tangl.prose.naming import (
    NamedActor, NamedConcept, NamedLocation, PersonalNamedActor, ProseBlock,
    get_authorities as naming_authorities,
)
from tangl.story import StoryGraph
from tangl.vm.runtime.frame import PhaseCtx


class NamedSword(NamedConcept, Node):
    """A graph-owned object, with no Actor/Location or personal-name schema."""


domain_dispatch = BehaviorRegistry(label="concept_naming_demo")


@domain_dispatch.register(task="story_ready")
def materialize_sword(*, caller: StoryGraph, **_kwargs: object) -> None:
    template = EntityTemplate(payload=NamedSword(**caller.locals["sword_spec"]))
    template.materialize(registry=caller)


@domain_dispatch.register(task="gather_ns")
def nominate_sword(*, ctx: PhaseCtx, **_kwargs: object) -> dict[str, NamedSword]:
    """Explicit world nomination, not a graph-wide concept namespace."""
    sword = ctx.graph.find_one(Selector(has_kind=NamedSword, label="sword"))
    # Entry selection can gather before story_ready materializes this fixture.
    return {"sword": sword} if sword is not None else {}


def get_authorities() -> list[BehaviorRegistry]:
    return [*naming_authorities(), domain_dispatch]
