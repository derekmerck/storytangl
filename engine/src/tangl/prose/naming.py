"""Opt-in provider naming and explicit authored introductions.

World domains import this extension before compilation and expose
``get_authorities()``. Raw prose remains opaque. ``ProseBlock`` segments carry
explicit references; template segments are the Python-native escape hatch.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum

from pydantic import Field

from tangl.core import BehaviorRegistry, DispatchLayer, Priority, Record
from tangl.journal.fragments import ChoiceFragment
from tangl.story import Actor, Block, Location, Role, Setting, get_narrator_key
from tangl.story.dispatch import do_render_text
from tangl.utils.enum_plus import EnumPlusMixin
from tangl.vm import ResolutionPhase
from tangl.vm.runtime.frame import PhaseCtx

from .dialog import DialogHandler, DialogMuBlock
from .mu_block import ConceptReference, MuBlock, ReferenceIntent


class NamingPolicy(EnumPlusMixin, str, Enum):
    CONCEALED = "concealed"
    PROPER = "proper"
    OFF = "off"


class HasNaming:
    """Optional authored wording and policy override on the provider itself."""

    anonymous_name: str = ""
    naming_policy: NamingPolicy | None = None


class NamingActor(HasNaming, Actor):
    """Actor adopting explicit prose naming vocabulary."""


class NamingLocation(HasNaming, Location):
    """Location adopting the same prose naming vocabulary as actors."""


class ProseBlock(Block):
    """Block carrying explicit ordered prose in addition to ordinary raw content."""

    prose: list[MuBlock | DialogMuBlock] = Field(
        default_factory=list, json_schema_extra={"include": True, "unstructurable": True},
    )
    choice_labels: dict[str, list[str | ConceptReference]] = Field(default_factory=dict)


Concept = Actor | Location
Referent = Concept | Role | Setting


class NamingOperations:
    """Shared naming resolver for semantic references, Jinja, and display labels."""

    def __init__(self, ctx: PhaseCtx) -> None:
        self.ctx = ctx

    def provider(self, target: Referent) -> Concept:
        concept = target.provider if isinstance(target, (Role, Setting)) else target
        if not isinstance(concept, (Actor, Location)):
            raise TypeError(f"Naming requires a bound actor/place provider at {target!r}")
        return concept

    def speaker(self, symbol: str) -> Concept:
        """Validate an authored symbol and dereference its current provider."""
        return self.provider(self.ctx.get_ns(self.ctx.cursor)[symbol])

    def policy(self, concept: Concept) -> NamingPolicy:
        if isinstance(concept, HasNaming) and concept.naming_policy is not None:
            return concept.naming_policy
        defaults = self.ctx.get_ns(self.ctx.cursor).get("naming_defaults", {})
        if not isinstance(defaults, Mapping):
            raise TypeError("naming_defaults must map provider kinds to naming policies")
        for kind in type(concept).__mro__:
            if kind.__name__ in defaults:
                return NamingPolicy(defaults[kind.__name__])
        return NamingPolicy.OFF

    def reference(
        self, target: Referent, intent: ReferenceIntent | str = ReferenceIntent.AUTO,
    ) -> str:
        concept = self.provider(target)
        intent = ReferenceIntent(intent)
        wording = do_render_text(concept, aspect=f"reference_{intent.value}", ctx=self.ctx)
        if wording is None:
            raise LookupError(f"No naming adapter for {concept.get_label()!r}")
        return wording

    def _reference(self, concept: Concept, intent: ReferenceIntent) -> str:
        """Realize the shipped minimal policy behind named text dispatch."""
        policy = self.policy(concept)
        knowledge = concept.peek_knowledge(get_narrator_key(self.ctx))
        anonymous = intent is ReferenceIntent.ANONYMOUS or (
            intent is ReferenceIntent.AUTO and policy is NamingPolicy.CONCEALED
            and (knowledge is None or knowledge.state != "IDENTIFIED")
        )
        if anonymous:
            if not isinstance(concept, HasNaming) or not concept.anonymous_name.strip():
                raise ValueError(
                    f"Missing anonymous_name for {concept.get_label()!r} "
                    f"while naming {self.ctx.cursor.get_label()!r}"
                )
            return concept.anonymous_name
        return concept.name or concept.get_label()

    def introduce(self, target: Referent) -> str:
        if self.ctx.current_phase not in {
            ResolutionPhase.UPDATE, ResolutionPhase.JOURNAL, ResolutionPhase.FINALIZE,
        }:
            raise RuntimeError("Introductions require UPDATE/FINALIZE or committed JOURNAL realization")
        concept = self.provider(target)
        wording = self.reference(concept, ReferenceIntent.PROPER)
        if self.policy(concept) is not NamingPolicy.OFF:
            knowledge = concept.get_knowledge(get_narrator_key(self.ctx))
            if knowledge.state != "IDENTIFIED":
                knowledge.state = "IDENTIFIED"
                knowledge.identification_source = f"prose:{self.ctx.cursor.uid}"
        return wording

    def realize(self, parts: list[str | ConceptReference], *, disclose: bool = False) -> str:
        ns = self.ctx.get_ns(self.ctx.cursor)
        output: list[str] = []
        for part in parts:
            if isinstance(part, str):
                output.append(part)
                continue
            target = ns[part.ref]
            if part.introduce:
                if not disclose:
                    raise ValueError(f"Introduction forbidden in display label: {part.ref!r}")
                output.append(self.introduce(target))
            else:
                output.append(self.reference(target, part.intent))
        return "".join(output)


naming_dispatch = BehaviorRegistry(
    label="prose.naming", default_dispatch_layer=DispatchLayer.AUTHOR,
)


@naming_dispatch.register(task="render_text")
def naming_text_aspect(
    *, caller: object, aspect: str, ctx: PhaseCtx, **_kwargs: object,
) -> str | None:
    if isinstance(caller, (Actor, Location)) and aspect in {
        "reference_auto", "reference_anonymous", "reference_proper",
    }:
        intent = ReferenceIntent(aspect.removeprefix("reference_"))
        return NamingOperations(ctx)._reference(caller, intent)
    return None


@naming_dispatch.register(task="gather_ns")
def naming_namespace(*, ctx: PhaseCtx, **_kwargs: object) -> dict[str, object]:
    operations = NamingOperations(ctx)
    return {"reference": operations.reference, "introduce": operations.introduce}


@naming_dispatch.register(task="render_journal", priority=Priority.EARLY)
def render_linked_prose(
    *, caller: Block, ctx: PhaseCtx, **_kwargs: object,
) -> list[Record] | None:
    if not isinstance(caller, ProseBlock):
        return None
    operations = NamingOperations(ctx)
    fragments = DialogHandler.render(
        caller.prose, ns=ctx.get_ns(caller), ctx=ctx, source_id=caller.uid,
        name_resolver=operations.reference,
        speaker_resolver=operations.speaker,
        parts_resolver=lambda parts: operations.realize(parts, disclose=True),
    )
    return fragments or None


@naming_dispatch.register(task="compose_journal", priority=Priority.LATE)
def name_linked_choices(
    *, fragments: list[Record], ctx: PhaseCtx, **_kwargs: object,
) -> list[Record] | None:
    if not isinstance(ctx.cursor, ProseBlock):
        return None
    operations = NamingOperations(ctx)
    output: list[Record] = []
    for fragment in fragments:
        if isinstance(fragment, ChoiceFragment):
            action = ctx.graph.get(fragment.edge_id)
            if action is not None and action.label in ctx.cursor.choice_labels:
                parts = ctx.cursor.choice_labels[action.label]
                fragment = fragment.model_copy(update={"text": operations.realize(parts)})
        output.append(fragment)
    return output


def get_authorities() -> list[BehaviorRegistry]:
    """World-domain adoption through the existing loader authority seam."""
    return [naming_dispatch]
