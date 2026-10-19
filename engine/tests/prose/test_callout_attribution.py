"""#576 scoped callout witnesses through the shared committed journal pipeline."""
from __future__ import annotations

import pytest

from tangl.core import Node, Selector
from tangl.journal.fragments import AttributedFragment, ContentFragment, fragment_to_dto
from tangl.mechanics.presence.look import HasSimpleLook
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.prose import ConceptReference, DialogHandler, DialogMuBlock, MuBlock
from tangl.prose.naming import (
    NamedActor, NamedConcept, NamingOperations, ProseBlock, discover_adoptions, naming_dispatch,
)
from tangl.story import Block, Player, Role, StoryGraph
from tangl.vm import Requirement, ResolutionPhase
from tangl.vm.dispatch import do_journal
from tangl.vm.runtime.frame import PhaseCtx


class NamedPlayer(NamedConcept, Player):
    """Explicit world composition, not an automatic opt-in for Player."""


class CalloutSword(NamedConcept, Node):
    pass


class CalloutVisibleActor(NamedActor, HasSimpleLook):
    """Naming and optional visual facets participate in the same dispatch."""


type CalloutScene = tuple[StoryGraph, ProseBlock, PhaseCtx]


def context(graph: StoryGraph, owner: Block, *, adopted: bool = True) -> PhaseCtx:
    ctx = PhaseCtx(graph=graph, cursor_id=owner.uid, current_phase=ResolutionPhase.JOURNAL)
    if adopted:
        ctx.local_authorities.append(naming_dispatch)
    ns = {label: graph.find_one(Selector(label=label)) for label in ("rin", "player", "sword")}
    ctx._ns_cache[owner.uid] = ns
    if adopted:
        naming = NamingOperations(ctx)
        ns.update({"reference": naming.reference, "introduce": naming.introduce,
                   "dialog_speaker_resolver": naming.speaker, "link_prose": True})
    return ctx


@pytest.fixture
def scene() -> CalloutScene:
    graph = StoryGraph()
    owner = ProseBlock(label="callouts", registry=graph)
    NamedActor(label="rin", name="Rin", anonymous_name="the blonde girl",
               naming_policy="concealed", registry=graph)
    NamedPlayer(label="player", name="Hero", anonymous_name="a traveler",
                naming_policy="concealed", proper_forms={"label": "You"}, registry=graph)
    CalloutSword(label="sword", name="Dawn", anonymous_name="an old sword",
               naming_policy="concealed", registry=graph)
    return graph, owner, context(graph, owner)


def journal(owner: Block, ctx: PhaseCtx) -> list[ContentFragment]:
    result = do_journal(owner, ctx=ctx)
    return result if isinstance(result, list) else [result]


@pytest.mark.parametrize("path", ["raw", "parsed", "json"])
@pytest.mark.parametrize("header", [
    "[!rin.angry]", "[!rin.angry] Rin", "[!dialog|rin.angry]",
    "[!.angry] Rin", "[!dialog|angry] Rin",
])
def test_auto_attribution_before_and_after_intro_is_pure_and_not_literal(
    scene: CalloutScene, header: str, path: str,
) -> None:
    graph, owner, ctx = scene
    source = f"> {header}\n> Hello."
    owner.prose = [MuBlock(text=source)] if path == "raw" else DialogHandler.parse(source)
    if path == "json":
        graph = StoryGraph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
        owner = graph.get(owner.uid)
        ctx = context(graph, owner)
    authored = [unit.unstructure() for unit in owner.prose]
    rin = ctx.get_ns(owner)["rin"]
    before = graph.value_hash()
    [first] = journal(owner, ctx)
    assert isinstance(first, AttributedFragment)
    assert first.who == "the blonde girl" and first.speaker_id == str(rin.uid)
    assert first.speaker_key == "rin" and first.speaker_attitude == "angry"
    assert first.dialog_mode == "dialog" and first.how == "dialog.angry"
    assert rin.narrator_knowledge == {} and graph.value_hash() == before
    historical = fragment_to_dto(first)
    NamingOperations(ctx).introduce(rin)
    identified = graph.value_hash()
    [second] = journal(owner, ctx)
    assert second.who == "Rin" and second.speaker_id == first.speaker_id
    assert graph.value_hash() == identified
    assert fragment_to_dto(first) == historical
    assert [unit.unstructure() for unit in owner.prose] == authored


@pytest.mark.parametrize("title,expected", [
    ("Disgruntled Girl", "Disgruntled Girl"), (r"\Rin", "Rin"),
])
@pytest.mark.parametrize("path", ["parsed", "json"])
def test_literal_overrides_keep_identity_and_ignore_introduction(
    scene: CalloutScene, title: str, expected: str, path: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(NamedActor, "get_dialog_image",
                        lambda self, dialog_class: f"{self.label}.svg", raising=False)
    graph, owner, ctx = scene
    owner.prose = DialogHandler.parse(f"> [!rin.angry] {title}\n> Hello.")
    owner.prose[0].style_dict["color"] = "red"
    if path == "json":
        graph = StoryGraph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
        owner = graph.get(owner.uid)
        ctx = context(graph, owner)
    authored = [unit.unstructure() for unit in owner.prose]
    assert owner.prose[0].literal_label is title.startswith("\\")
    before = graph.value_hash()
    [first] = journal(owner, ctx)
    assert first.who == expected and first.speaker_id == str(ctx.get_ns(owner)["rin"].uid)
    assert first.media_payload["ref"] == "rin.svg" and graph.value_hash() == before
    assert first.presentation_hints.style_dict == {"color": "red"}
    NamingOperations(ctx).introduce(ctx.get_ns(owner)["rin"])
    assert journal(owner, ctx)[0].who == expected
    assert [unit.unstructure() for unit in owner.prose] == authored


def test_adopted_title_preserves_matched_form_and_auto_policy(scene: CalloutScene) -> None:
    graph, owner, ctx = scene
    rin = ctx.get_ns(owner)["rin"]
    rin.proper_forms["formal"] = "Ms. Northstar"
    owner.prose = DialogHandler.parse("> [!rin] Ms. Northstar\n> Hello.")
    before = graph.value_hash()
    assert journal(owner, ctx)[0].who == "the blonde girl"
    assert graph.value_hash() == before
    NamingOperations(ctx).introduce(rin)
    assert journal(owner, ctx)[0].who == "Ms. Northstar"


@pytest.mark.parametrize("path", ["ordinary", "ordinary_json", "raw", "parsed", "json"])
def test_titleless_label_default_does_not_replace_adopted_primary_or_formal_title(
    scene: CalloutScene, path: str,
) -> None:
    graph, owner, ctx = scene
    rin = ctx.get_ns(owner)["rin"]
    rin.proper_forms.update({"label": "Guide", "formal": "Ms. Northstar"})
    source = "\n\n".join(
        f"> [!rin.angry]{title}\n> Hello."
        for title in ("", " Rin", " Ms. Northstar", " Disgruntled Girl", r" \Rin")
    )
    if path.startswith("ordinary"):
        owner = Block(label="raw_callouts", content=source, registry=graph)
        ctx = context(graph, owner)
    else:
        owner.prose = [MuBlock(text=source)] if path == "raw" else DialogHandler.parse(source)
    if "json" in path:
        graph = StoryGraph.structure(Json.deserialize(Json.serialize(graph.unstructure())))
        owner = graph.get(owner.uid)
        ctx = context(graph, owner)
        rin = ctx.get_ns(owner)["rin"]
    authored = owner.unstructure()
    adoptions = discover_adoptions(ctx.get_ns(owner))
    matched = {title: [ref.unstructure() for ref in refs] for title, refs in adoptions.items()}
    before = graph.value_hash()
    first = journal(owner, ctx)
    assert [fragment.who for fragment in first] == [
        "the blonde girl", "the blonde girl", "the blonde girl", "Disgruntled Girl", "Rin",
    ]
    assert graph.value_hash() == before and rin.narrator_knowledge == {}
    historical = [fragment_to_dto(fragment) for fragment in first]
    NamingOperations(ctx).introduce(rin)
    identified = graph.value_hash()
    second = journal(owner, ctx)
    assert [fragment.who for fragment in second] == [
        "Guide", "Rin", "Ms. Northstar", "Disgruntled Girl", "Rin",
    ]
    assert all(fragment.speaker_id == str(rin.uid) and fragment.speaker_key == "rin"
               and fragment.how == "dialog.angry" for fragment in [*first, *second])
    assert graph.value_hash() == identified
    assert [fragment_to_dto(fragment) for fragment in first] == historical
    assert owner.unstructure() == authored
    assert {title: [ref.unstructure() for ref in refs]
            for title, refs in adoptions.items()} == matched
    assert {title: [ref.unstructure() for ref in refs]
            for title, refs in discover_adoptions(ctx.get_ns(owner)).items()} == matched


def test_naming_label_form_coexists_with_presence_text_dispatch(scene: CalloutScene) -> None:
    import tangl.mechanics.presence.presentation  # noqa: F401

    graph, owner, ctx = scene
    actor = CalloutVisibleActor(label="visible", name="Rin", anonymous_name="the girl",
                               proper_forms={"label": "Guide"}, naming_policy="concealed",
                               registry=graph)
    ctx.get_ns(owner)["visible"] = actor
    owner.prose = [DialogMuBlock(dialog_class="visible", text="Hello.")]
    assert journal(owner, ctx)[0].who == "the girl"
    NamingOperations(ctx).introduce(actor)
    assert journal(owner, ctx)[0].who == "Guide"


@pytest.mark.parametrize("symbol,anonymous,proper", [
    ("player", "a traveler", "You"), ("sword", "an old sword", "Dawn"),
])
def test_generic_named_attribution_needs_no_actor_or_media(
    scene: CalloutScene, symbol: str, anonymous: str, proper: str,
) -> None:
    graph, owner, ctx = scene
    owner.prose = [MuBlock(text=f"> [!{symbol}]\n> Speaking.")]
    before = graph.value_hash()
    [first] = journal(owner, ctx)
    assert first.who == anonymous and first.media_payload is None
    assert graph.value_hash() == before
    NamingOperations(ctx).introduce(ctx.get_ns(owner)[symbol])
    assert journal(owner, ctx)[0].who == proper
    assert "You" not in discover_adoptions(ctx.get_ns(owner))


def test_namespace_does_not_select_mode_and_note_does_not_invent_narrator(
    scene: CalloutScene,
) -> None:
    graph, owner, ctx = scene
    owner.prose = [MuBlock(text="> [!note|]\n> A note.")]
    [note] = journal(owner, ctx)
    assert not isinstance(note, AttributedFragment) and note.content == "A note."
    owner.prose = DialogHandler.parse("> [!note]\n> Hello.")
    assert owner.prose[0].dialog_mode == "dialog"
    with pytest.raises(ValueError, match="source.*dialog requires.*note"):
        journal(owner, ctx)
    ctx.get_ns(owner)["note"] = ctx.get_ns(owner)["rin"]
    assert journal(owner, ctx)[0].dialog_mode == "dialog"


def test_unbound_chain_remains_presentation_on_non_attributed_note(scene: CalloutScene) -> None:
    _graph, owner, ctx = scene
    owner.prose = [MuBlock(text="> [!note|important]\n> A note.")]
    [note] = journal(owner, ctx)
    assert not isinstance(note, AttributedFragment)
    assert note.content == "A note."
    assert "dialog_class:note_important" in note.presentation_hints.style_tags
    assert "attitude:important" in note.presentation_hints.style_tags


def test_missing_ambiguous_and_conflicting_bindings_have_source_diagnostics(
    scene: CalloutScene,
) -> None:
    graph, owner, ctx = scene
    owner.prose = [MuBlock(text="> [!unknown]\n> Hello.")]
    with pytest.raises(ValueError, match=str(owner.uid)):
        journal(owner, ctx)
    owner.prose = [MuBlock(text="> [!rin.angry] Dawn\n> Hello.")]
    before = graph.value_hash()
    with pytest.raises(ValueError, match="callouts.*conflicting.*rin.*Dawn"):
        journal(owner, ctx)
    assert graph.value_hash() == before
    rin = ctx.get_ns(owner)["rin"]
    first = Role(label="first", registry=graph, requirement=Requirement(has_kind=NamedActor))
    second = Role(label="second", registry=graph, requirement=Requirement(has_kind=NamedActor))
    first.set_provider(rin)
    second.set_provider(rin)
    ctx.get_ns(owner).update({"first": first, "second": second})
    owner.prose = [MuBlock(text="> [!first] Rin\n> Hello.")]
    with pytest.raises(ValueError, match="ambiguous.*Rin.*first.*second"):
        journal(owner, ctx)


def test_wrapper_alias_and_corresponding_provider_title_agree(scene: CalloutScene) -> None:
    graph, owner, ctx = scene
    rin = ctx.get_ns(owner).pop("rin")
    role = Role(label="host", registry=graph, requirement=Requirement(has_kind=NamedActor))
    role.set_provider(rin)
    ctx.get_ns(owner).update({"host": rin, "host_role": role, "host_alias": role})
    owner.prose = [MuBlock(text="> [!host_role.angry] Rin\n> Hello.")]
    [speaker] = journal(owner, ctx)
    assert speaker.who == "the blonde girl" and speaker.speaker_key == "host_role"
    assert speaker.speaker_id == str(rin.uid) and rin.narrator_knowledge == {}


def test_structured_label_precedes_own_body_and_templates_execute_once(scene: CalloutScene) -> None:
    graph, owner, ctx = scene
    calls: list[str] = []

    def body() -> str:
        calls.append("body")
        return "{{ not_executed }}"

    ctx.get_ns(owner)["body"] = body
    owner.prose = [
        DialogMuBlock(dialog_class="rin.angry", label="Rin", text=[
            "I am ", ConceptReference(ref="rin", introduce=True), ".",
        ]),
        DialogMuBlock(dialog_class="rin", label="Rin", template="{{ body() }}"),
    ]
    before = [unit.unstructure() for unit in owner.prose]
    first, second = journal(owner, ctx)
    assert first.who == "the blonde girl" and first.content == "I am Rin."
    assert second.who == "Rin" and second.content == "{{ not_executed }}"
    assert calls == ["body"]
    assert [unit.unstructure() for unit in owner.prose] == before


def test_vanilla_world_retains_literal_fallback_and_plain_player_is_not_opted_in() -> None:
    graph = StoryGraph()
    player = Player(registry=graph)
    owner = Block(content="> [!dialog|] Stranger\n> Hello.", registry=graph)
    ctx = context(graph, owner, adopted=False)
    ctx.get_ns(owner)["player"] = player
    [speaker] = journal(owner, ctx)
    assert speaker.who == "Stranger" and speaker.speaker_id is None
    assert not isinstance(player, NamedConcept)
    assert "narrator_knowledge" not in type(player).model_fields
    assert "dialog_speaker_resolver" not in ctx.get_ns(owner)
