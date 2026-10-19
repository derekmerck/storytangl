"""Opt-in provider naming and explicit authored introductions.

World domains import this extension before compilation and expose
``get_authorities()``. Raw prose remains opaque. ``ProseBlock`` segments carry
explicit references; template segments are the Python-native escape hatch.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from uuid import UUID

from pydantic import Field

from tangl.core import BehaviorRegistry, DispatchLayer, Priority, Record
from tangl.journal.fragments import ChoiceFragment
from tangl.lang.personal_name import PersonalName
from tangl.story import Actor, Block, Location, Role, Setting, get_narrator_key
from tangl.story.concepts.narrator_knowledge import HasNarratorKnowledge
from tangl.story.dispatch import do_render_text
from tangl.utils.enum_plus import EnumPlusMixin
from tangl.vm import ResolutionPhase
from tangl.vm.runtime.frame import PhaseCtx

from .dialog import DialogHandler, DialogMuBlock
from .linking import AdoptionTable, prepare_prose
from .mu_block import (
    ConceptReference, DialogSpeakerBinding, MuBlock, RealizationParams, RealizationValue,
    ReferenceIntent,
)


class NamingPolicy(EnumPlusMixin, str, Enum):
    CONCEALED = "concealed"
    PROPER = "proper"
    OFF = "off"


class NamedConcept(HasNarratorKnowledge):
    """Optional concept-local wording, adoption data, and explicit identification.

    Compose with an Entity/Node, not an embedded manager. Forms request wording;
    only introduction changes knowledge. Worlds may override nominal selection
    here or through normal named-text dispatch.
    """

    name: str = ""
    anonymous_name: str = ""
    naming_policy: NamingPolicy | None = None
    proper_forms: dict[str, str] = Field(default_factory=dict, json_schema_extra={"include": True})
    proper_aliases: dict[str, RealizationParams] = Field(
        default_factory=dict, json_schema_extra={"include": True},
    )

    def _proper_forms(self) -> dict[str, str]:
        return self.proper_forms

    def adopts(self) -> dict[str, RealizationParams]:
        """Discover data-only proper spellings, never anonymous descriptions.

        The display name wins generated duplicates, then the first declared
        form. Explicit alias parameters override both; returned data is detached.
        """
        result = {self.name: {}} if self.name else {}
        for form, spelling in self._proper_forms().items():
            if form != "label":
                result.setdefault(spelling, {"form": form})
        result.update({spelling: dict(params) for spelling, params in self.proper_aliases.items()})
        return result

    def _proper_nominal(self, *, form: str | None = None, **_params: RealizationValue) -> str:
        # Form requests are extensible intent, not an enum or a dispatch gate.
        nominal = self.name or self.get_label()
        return self._proper_forms().get(form, nominal) if form is not None else nominal

    def get_nominal(
        self, narrator_key: str = "_", *, policy: NamingPolicy | None = None,
        intent: ReferenceIntent | str = ReferenceIntent.AUTO, **params: RealizationValue,
    ) -> str:
        """Select wording without creating a narrator record or disclosing identity."""
        intent = ReferenceIntent(intent)
        policy = policy if policy is not None else self.naming_policy or NamingPolicy.OFF
        knowledge = self.peek_knowledge(narrator_key)
        anonymous = intent is ReferenceIntent.ANONYMOUS or (
            intent is ReferenceIntent.AUTO and policy is NamingPolicy.CONCEALED
            and (knowledge is None or knowledge.state != "IDENTIFIED")
        )
        if anonymous:
            if not self.anonymous_name.strip():
                raise ValueError(f"Missing anonymous_name for {self.get_label()!r}")
            return self.anonymous_name
        return self._proper_nominal(**params)

    def introduce(
        self, narrator_key: str = "_", *, policy: NamingPolicy | None = None,
        source: str | None = None, **params: RealizationValue,
    ) -> str:
        """Explicit idempotent identification; phase-aware authors use the helper."""
        wording = self.get_nominal(narrator_key, policy=policy, intent=ReferenceIntent.PROPER,
                                   **params)
        policy = policy if policy is not None else self.naming_policy or NamingPolicy.OFF
        if policy is not NamingPolicy.OFF:
            knowledge = self.get_knowledge(narrator_key)
            if knowledge.state != "IDENTIFIED":
                knowledge.state = "IDENTIFIED"
                knowledge.identification_source = source
        return wording


class NamedActor(NamedConcept, Actor):
    """Actor adopting explicit prose naming vocabulary."""


class NamedLocation(NamedConcept, Location):
    """Location adopting the same prose naming vocabulary as actors."""


class PersonalNamedActor(NamedActor):
    """Optional personal-name enrichment; basic actors/items need no name parsing."""

    personal_name: PersonalName | None = Field(
        default=None, json_schema_extra={"include": True, "unstructurable": True},
    )

    def _proper_forms(self) -> dict[str, str]:
        generated = self.personal_name.forms() if self.personal_name is not None else {}
        return generated | self.proper_forms


def _scoped_named_bindings(ns: Mapping[str, object]) -> dict[str, tuple[str, NamedConcept]]:
    """Share the existing wrapper/alias equivalence for discovery and headers."""
    wrappers: dict[UUID, tuple[str, Role | Setting]] = {}
    for symbol, value in sorted(ns.items()):
        if isinstance(value, (Role, Setting)) and isinstance(value.provider, NamedConcept):
            wrappers.setdefault(value.uid, (symbol, value))
    bindings: dict[str, tuple[str, NamedConcept]] = {}
    for symbol, value in sorted(ns.items()):
        if isinstance(value, (Role, Setting)) and isinstance(value.provider, NamedConcept):
            bindings[symbol] = (wrappers[value.uid][0], value.provider)
            continue
        if not isinstance(value, NamedConcept):
            continue
        corresponding = [
            key for key, wrapper in wrappers.values()
            if wrapper.get_label() == symbol and wrapper.provider is value
        ]
        bindings[symbol] = (corresponding[0] if len(corresponding) == 1 else symbol, value)
    return bindings


def discover_adoptions(ns: Mapping[str, object]) -> AdoptionTable:
    """Discover afforded spellings without collapsing independent roles/providers."""
    bindings = {symbol: concept for symbol, concept in _scoped_named_bindings(ns).values()}
    adoptions: AdoptionTable = {}
    for symbol, concept in sorted(bindings.items()):
        for spelling, params in concept.adopts().items():
            if spelling:
                adoptions.setdefault(spelling, []).append(
                    ConceptReference(ref=symbol, params=dict(params)),
                )
    return adoptions


class ProseBlock(Block):
    """Block carrying explicit ordered prose in addition to ordinary raw content."""

    prose: list[MuBlock | DialogMuBlock] = Field(
        default_factory=list, json_schema_extra={"include": True, "unstructurable": True},
    )
    choice_labels: dict[str, list[str | ConceptReference]] = Field(default_factory=dict)


Concept = NamedConcept | Actor | Location
Referent = Concept | Role | Setting


class NamingOperations:
    """Shared naming resolver for semantic references, Jinja, and display labels."""

    def __init__(self, ctx: PhaseCtx) -> None:
        self.ctx = ctx

    def provider(self, target: Referent) -> Concept:
        concept = target.provider if isinstance(target, (Role, Setting)) else target
        if not isinstance(concept, (NamedConcept, Actor, Location)):
            raise TypeError(f"Naming requires a bound concept provider at {target!r}")
        return concept

    def speaker(
        self, symbol: str | None, title: str | None = None, literal: bool = False,
    ) -> DialogSpeakerBinding | None:
        """Reconcile an exact header binding and whole-title scoped adoption, purely."""
        ns = self.ctx.get_ns(self.ctx.cursor)
        source = f"owner {self.ctx.cursor.get_label()} ({self.ctx.cursor.uid})"
        target = ns.get(symbol) if symbol else None
        binding = None
        if isinstance(target, (NamedConcept, Actor, Location, Role, Setting)):
            if isinstance(target, (Role, Setting)) and target.provider is None:
                raise TypeError(f"{source}: unbound dialog binding {symbol!r}")
            binding = DialogSpeakerBinding(key=symbol, subject=self.provider(target))
        references = discover_adoptions(ns).get(title, []) if title and not literal else []
        if len(references) > 1:
            raise ValueError(
                f"{source}: ambiguous dialog title {title!r}; candidates: "
                + ", ".join(reference.ref for reference in references)
            )
        if references:
            reference = references[0]
            canonical = _scoped_named_bindings(ns)
            if binding is not None and (
                symbol not in canonical or canonical[symbol][0] != reference.ref
            ):
                raise ValueError(
                    f"{source}: conflicting dialog binding {symbol!r} and title {title!r} "
                    f"({reference.ref!r})"
                )
            if binding is None:
                binding = DialogSpeakerBinding(
                    key=reference.ref, subject=self.provider(ns[reference.ref]),
                )
            binding.title_reference = reference
        return binding

    def label(self, target: Referent, **params: RealizationValue) -> str:
        params.setdefault("form", "label")
        return self.reference(target, **params)

    def policy(self, concept: Concept) -> NamingPolicy:
        if isinstance(concept, NamedConcept) and concept.naming_policy is not None:
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
        **params: RealizationValue,
    ) -> str:
        concept = self.provider(target)
        intent = ReferenceIntent(intent)
        wording = do_render_text(concept, aspect=f"reference_{intent.value}", ctx=self.ctx,
                                 **params)
        if wording is None:
            raise LookupError(f"No naming adapter for {concept.get_label()!r}")
        return wording

    def _reference(
        self, concept: Concept, intent: ReferenceIntent, **params: RealizationValue,
    ) -> str:
        """Realize the shipped minimal policy behind named text dispatch."""
        policy = self.policy(concept)
        if isinstance(concept, NamedConcept):
            return concept.get_nominal(get_narrator_key(self.ctx), policy=policy,
                                       intent=intent, **params)
        knowledge = concept.peek_knowledge(get_narrator_key(self.ctx))
        if intent is ReferenceIntent.ANONYMOUS or (
            intent is ReferenceIntent.AUTO and policy is NamingPolicy.CONCEALED
            and (knowledge is None or knowledge.state != "IDENTIFIED")
        ):
            raise ValueError(f"Missing anonymous_name for {concept.get_label()!r}")
        return concept.name or concept.get_label()

    def introduce(self, target: Referent, **params: RealizationValue) -> str:
        if self.ctx.current_phase not in {
            ResolutionPhase.UPDATE, ResolutionPhase.JOURNAL, ResolutionPhase.FINALIZE,
        }:
            raise RuntimeError("Introductions require UPDATE/FINALIZE or committed JOURNAL realization")
        concept = self.provider(target)
        wording = self.reference(concept, ReferenceIntent.PROPER, **params)
        if isinstance(concept, NamedConcept):
            concept.introduce(get_narrator_key(self.ctx), policy=self.policy(concept),
                              source=f"prose:{self.ctx.cursor.uid}", **params)
            return wording
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
                output.append(self.introduce(target, **part.params))
            else:
                output.append(self.reference(target, part.intent, **part.params))
        return "".join(output)


naming_dispatch = BehaviorRegistry(
    label="prose.naming", default_dispatch_layer=DispatchLayer.AUTHOR,
)


@naming_dispatch.register(task="render_text")
def naming_text_aspect(
    *, caller: object, aspect: str, ctx: PhaseCtx,
    **params: RealizationValue,
) -> str | None:
    if isinstance(caller, (NamedConcept, Actor, Location)) and aspect in {
        "reference_auto", "reference_anonymous", "reference_proper",
    }:
        intent = ReferenceIntent(aspect.removeprefix("reference_"))
        return NamingOperations(ctx)._reference(caller, intent, **params)
    return None


@naming_dispatch.register(task="gather_ns")
def naming_namespace(*, ctx: PhaseCtx, **_kwargs: object) -> dict[str, object]:
    operations = NamingOperations(ctx)
    return {
        "reference": operations.reference, "introduce": operations.introduce,
        "dialog_speaker_resolver": operations.speaker,
    }


@naming_dispatch.register(task="render_journal", priority=Priority.EARLY)
def render_linked_prose(
    *, caller: Block, ctx: PhaseCtx, **_kwargs: object,
) -> list[Record] | None:
    if not isinstance(caller, ProseBlock):
        return None
    operations = NamingOperations(ctx)
    ns = ctx.get_ns(caller)
    units = caller.prose
    if ns.get("link_prose", False) is True:
        units = prepare_prose(units, discover_adoptions(ns),
                              source=f"owner {caller.get_label()} ({caller.uid})")
    fragments = DialogHandler.render(
        units, ns=ns, ctx=ctx, source_id=caller.uid,
        name_resolver=operations.label,
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
