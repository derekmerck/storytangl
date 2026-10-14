"""Generic concept naming, form intent, pure discovery, and owner persistence."""
from __future__ import annotations

import json

import pytest

from tangl.core import Node, Selector
from tangl.lang.personal_name import PersonalName
from tangl.persistence.serializers import JsonSerializationHandler
from tangl.prose import DialogMuBlock, MuBlock
from tangl.prose.mu_block import ConceptReference, RealizationValue, ReferenceIntent
from tangl.prose.naming import (
    NamedActor, NamedConcept, NamedLocation, NamingOperations, NamingPolicy,
    PersonalNamedActor, ProseBlock, naming_dispatch, render_linked_prose,
)
from tangl.story import Actor, Role, StoryGraph
from tangl.vm import Requirement, ResolutionPhase
from tangl.vm.runtime.frame import PhaseCtx


class NamedItem(NamedConcept, Node):
    """No person/place schema is needed to participate."""


class QuietItem(NamedItem):
    def get_nominal(
        self, narrator_key: str = "_", *, policy: NamingPolicy | None = None,
        intent: ReferenceIntent | str = ReferenceIntent.AUTO, **params: RealizationValue,
    ) -> str:
        if ReferenceIntent(intent) is ReferenceIntent.AUTO:
            return self.anonymous_name
        return super().get_nominal(narrator_key, policy=policy, intent=intent, **params)


def context(graph: StoryGraph, owner: ProseBlock) -> PhaseCtx:
    ctx = PhaseCtx(graph=graph, cursor_id=owner.uid, current_phase=ResolutionPhase.JOURNAL)
    ctx.local_authorities.append(naming_dispatch)
    ctx._ns_cache[owner.uid] = {
        "naming_defaults": {"NamedConcept": "concealed"},
    }
    return ctx


@pytest.mark.parametrize("kind", [NamedActor, NamedLocation, NamedItem, QuietItem])
def test_one_contract_pure_discovery_and_isolated_identification(kind: type[NamedConcept]) -> None:
    graph = StoryGraph()
    owner = ProseBlock(label="start", registry=graph)
    concept = kind(label="named", name="Dawn", anonymous_name="a glint", registry=graph)
    ctx = context(graph, owner)
    operations = NamingOperations(ctx)
    before = graph.value_hash()
    assert graph.find_one(Selector(has_kind=NamedConcept)) is concept
    assert concept.adopts() == {"Dawn": {}}
    assert "a glint" not in concept.adopts()
    assert concept.get_nominal(policy=NamingPolicy.CONCEALED) == "a glint"
    assert operations.reference(concept) == "a glint"
    assert operations.reference(concept, "proper") == "Dawn"
    ctx.get_ns(owner)
    assert concept.narrator_knowledge == {}
    assert graph.value_hash() == before
    assert operations.introduce(concept) == "Dawn"
    identified = graph.value_hash()
    assert operations.introduce(concept) == "Dawn"
    assert graph.value_hash() == identified
    assert operations.reference(concept) == ("a glint" if kind is QuietItem else "Dawn")
    assert operations.reference(concept, "anonymous") == "a glint"
    other = ctx.derive(meta={"narrator_key": "other"})
    other._ns_cache[owner.uid] = ctx.get_ns(owner)
    assert NamingOperations(other).reference(concept) == "a glint"
    assert "other" not in concept.narrator_knowledge
    assert graph.value_hash() == identified


def test_personal_forms_preserve_intent_without_forcing_knowledge() -> None:
    graph = StoryGraph()
    actor = PersonalNamedActor(
        label="jon", name="Jonathan", anonymous_name="a stranger", registry=graph,
        personal_name=PersonalName(
            given_name="Jonathan", family_name="Smith", nickname="Jack", title="Dr.",
            aliases={"Johnny"},
        ),
    )
    owner = ProseBlock(label="start", registry=graph)
    ctx = context(graph, owner)
    operations = NamingOperations(ctx)
    before = graph.value_hash()
    adoption = actor.adopts()
    assert json.loads(json.dumps(adoption)) == adoption
    assert adoption["Dr. Smith"] == {"form": "formal"}
    assert adoption["Jack"] == {"form": "familiar"}
    assert adoption["Johnny"] == {"form": "alias:Johnny"}
    assert "a stranger" not in adoption
    for spelling, params in adoption.items():
        assert operations.reference(actor, **params) == "a stranger"
        assert operations.reference(actor, "proper", **params) == spelling
    assert operations.reference(actor, form="proper") == "a stranger"
    assert graph.value_hash() == before
    assert actor.narrator_knowledge == {}
    operations.introduce(actor)
    for spelling, params in adoption.items():
        assert operations.reference(actor, **params) == spelling
    assert operations.reference(actor, "anonymous", form="formal") == "a stranger"
    assert actor.name == "Jonathan"


def test_duplicate_forms_have_stable_precedence_and_explicit_author_overrides() -> None:
    actor = PersonalNamedActor(
        name="Rin", anonymous_name="the blonde girl",
        personal_name=PersonalName(given_name="Rin", nickname="Rin", title=""),
    )
    assert actor.adopts()["Rin"] == {}
    actor.name = "Display"
    assert actor.adopts()["Rin"] == {"form": "proper"}
    actor.proper_forms["short"] = "Rin"
    actor.proper_aliases["Rin"] = {"form": "short"}
    before = actor.unstructure()
    adoption = actor.adopts()
    assert adoption["Rin"] == {"form": "short"}
    adoption["Rin"]["form"] = "formal"
    assert actor.unstructure() == before


def test_generic_defaults_override_opt_out_and_diagnostic_anonymous_wording() -> None:
    graph = StoryGraph()
    item = NamedItem(label="sword", name="Dawn", registry=graph)
    owner = ProseBlock(registry=graph)
    ctx = context(graph, owner)
    operations = NamingOperations(ctx)
    with pytest.raises(ValueError, match="Missing anonymous_name.*sword"):
        operations.reference(item)
    ctx.get_ns(owner)["naming_defaults"]["NamedItem"] = "proper"
    assert operations.reference(item) == "Dawn"
    item.naming_policy = NamingPolicy.CONCEALED
    with pytest.raises(ValueError, match="anonymous_name"):
        operations.reference(item)
    item.naming_policy = NamingPolicy.OFF
    assert operations.introduce(item) == "Dawn"
    assert item.narrator_knowledge == {}


def test_two_roles_share_provider_knowledge_and_recasting_does_not_transfer_it() -> None:
    graph = StoryGraph()
    actor = NamedActor(name="Rin", anonymous_name="the blonde girl", registry=graph)
    replacement = NamedActor(name="Beth", anonymous_name="the dark-haired girl", registry=graph)
    owner = ProseBlock(registry=graph)
    first = Role(registry=graph, requirement=Requirement(has_kind=Actor))
    second = Role(registry=graph, requirement=Requirement(has_kind=Actor))
    first.set_provider(actor)
    second.set_provider(actor)
    operations = NamingOperations(context(graph, owner))
    assert operations.introduce(first) == "Rin"
    before = graph.value_hash()
    assert operations.introduce(second) == "Rin"
    assert graph.value_hash() == before
    assert first.narrator_knowledge == second.narrator_knowledge == {}
    second.set_provider(replacement)
    assert operations.reference(second) == "the dark-haired girl"
    assert replacement.narrator_knowledge == {}
    assert operations.reference(first) == "Rin"


@pytest.mark.parametrize("flat_json", [False, True])
def test_owner_graph_retains_personal_names_reference_params_and_knowledge(flat_json: bool) -> None:
    graph = StoryGraph()
    owner = ProseBlock(label="start", registry=graph)
    actor = PersonalNamedActor(
        label="rin", name="Rin", anonymous_name="the blonde girl", registry=graph,
        personal_name=PersonalName(given_name="Rin", family_name="Northstar", title="Ms."),
    )
    actor.personal_name.aliases.add("Rinnie")
    actor.proper_aliases["Ms. Northstar"] = {"form": "formal"}
    reference = ConceptReference(ref="host")
    reference.params["form"] = "formal"
    owner.prose.append(MuBlock(text=[reference]))
    ctx = context(graph, owner)
    ctx.get_ns(owner)["host"] = actor
    NamingOperations(ctx).introduce(actor)
    data = graph.unstructure()
    if flat_json:
        data = JsonSerializationHandler.deserialize(JsonSerializationHandler.serialize(data))
    restored = StoryGraph.structure(data)
    restored_actor = restored.get(actor.uid)
    restored_owner = restored.get(owner.uid)
    assert type(restored_actor) is PersonalNamedActor
    assert type(restored_actor.personal_name) is PersonalName
    assert restored_actor.personal_name.aliases == {"Rinnie"}
    assert restored_actor.proper_aliases == actor.proper_aliases
    assert restored_actor.peek_knowledge().state == "IDENTIFIED"
    assert type(restored_owner.prose[0].text[0]) is ConceptReference
    assert restored_owner.prose[0].text[0].params == {"form": "formal"}
    assert set(restored.members) == set(graph.members)
    assert restored.unstructure() == graph.unstructure()
    restored_ctx = context(restored, restored_owner)
    restored_ctx.get_ns(restored_owner)["host"] = restored_actor
    before = restored.value_hash()
    assert render_linked_prose(caller=restored_owner, ctx=restored_ctx)[0].content == "Ms. Northstar"
    assert restored.value_hash() == before


def test_semantic_and_template_forms_share_ordered_policy_and_generated_words_stay_literal() -> None:
    graph = StoryGraph()
    owner = ProseBlock(label="start", registry=graph)
    actor = NamedActor(
        label="rin", name="Rin", anonymous_name="the blonde girl", registry=graph,
        proper_forms={"formal": "{{ introduce(host) }}"},
    )
    ctx = context(graph, owner)
    operations = NamingOperations(ctx)
    ctx.get_ns(owner).update({"host": actor, "reference": operations.reference,
                              "introduce": operations.introduce})
    owner.prose = [
        MuBlock(text=[ConceptReference(ref="host", params={"form": "formal"})]),
        DialogMuBlock(label="host", dialog_class="NPC.happy",
                      template="{{ introduce(host, form='formal') }}"),
        DialogMuBlock(label="host", dialog_class="NPC.happy",
                      template="{{ reference(host, form='formal') }}"),
    ]
    fragments = render_linked_prose(caller=owner, ctx=ctx)
    assert [f.content for f in fragments] == [
        "the blonde girl", "{{ introduce(host) }}", "{{ introduce(host) }}",
    ]
    assert [f.speaker_name for f in fragments[1:]] == ["the blonde girl", "Rin"]
    assert all(f.speaker_attitude == "happy" for f in fragments[1:])
    before = graph.value_hash()
    operations.reference(actor, "proper", form="formal")
    assert graph.value_hash() == before


def test_named_object_is_not_automatically_a_speaker() -> None:
    graph = StoryGraph()
    owner = ProseBlock(registry=graph)
    item = NamedItem(name="Dawn", anonymous_name="an old sword", registry=graph)
    ctx = context(graph, owner)
    ctx.get_ns(owner)["sword"] = item
    before = graph.value_hash()
    assert NamingOperations(ctx).reference(item) == "an old sword"
    with pytest.raises(TypeError, match="Not a speaker"):
        NamingOperations(ctx).speaker("sword")
    assert graph.value_hash() == before


def test_intentionally_non_adopted_actor_floor_uses_existing_name_and_knowledge() -> None:
    graph = StoryGraph()
    owner = ProseBlock(registry=graph)
    actor = Actor(name="Ordinary", registry=graph)
    ctx = context(graph, owner)
    ctx.get_ns(owner)["naming_defaults"]["Actor"] = "proper"
    operations = NamingOperations(ctx)
    before = graph.value_hash()
    assert operations.reference(actor) == "Ordinary"
    assert graph.value_hash() == before
    assert actor.narrator_knowledge == {}
    assert operations.introduce(actor) == "Ordinary"
    assert actor.peek_knowledge().state == "IDENTIFIED"
