"""Pure namespace discovery, conservative lexical lowering, and shared preparation."""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
from uuid import UUID

import pytest

from tangl.core import Node
from tangl.journal.fragments import ContentFragment
from tangl.prose import DialogHandler, DialogMuBlock, MuBlock
from tangl.prose.linking import link_text, prepare_prose
from tangl.prose.mu_block import (
    ConceptReference, NameResolver, RealizationParams, RealizationValue,
    ReferenceIntent, SpeakerResolver,
)
from tangl.prose.naming import (
    NamedActor, NamedConcept, NamedLocation, NamingOperations, NamingPolicy, PersonalNamedActor,
    ProseBlock, discover_adoptions, naming_dispatch,
)
from tangl.lang.personal_name import PersonalName
from tangl.story import Actor, Role, Setting, StoryGraph
from tangl.vm import Requirement, ResolutionPhase
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.ctx import VmPhaseCtx


class NamedItem(NamedConcept, Node):
    pass


class QuietRelic(NamedItem):
    def adopts(self) -> dict[str, RealizationParams]:
        return {"Unmarked Relic": {"form": "inscription"}}

    def get_nominal(
        self, narrator_key: str = "_", *, policy: NamingPolicy | None = None,
        intent: ReferenceIntent | str = ReferenceIntent.AUTO, **params: RealizationValue,
    ) -> str:
        if ReferenceIntent(intent) is ReferenceIntent.AUTO:
            return self.anonymous_name
        return super().get_nominal(narrator_key, policy=policy, intent=intent, **params)


class CustomNarration(MuBlock):
    emphasis: str = "custom"

    def prepare_fragment(
        self, *, source_id: UUID | None = None, ns: Mapping[str, object] | None = None,
        ctx: VmPhaseCtx | None = None, name_resolver: NameResolver | None = None,
        speaker_resolver: SpeakerResolver | None = None,
    ) -> ContentFragment:
        fragment = super().prepare_fragment(
            source_id=source_id, ns=ns, ctx=ctx, name_resolver=name_resolver,
            speaker_resolver=speaker_resolver,
        )
        return fragment.model_copy(update={"tags": {self.emphasis}})


@pytest.fixture
def forms() -> dict[str, list[ConceptReference]]:
    return {"Rin": [ConceptReference(ref="host_role")]}


def surface(parts: list[str | ConceptReference]) -> str:
    return "".join(part if isinstance(part, str) else "Rin" for part in parts)


@pytest.mark.parametrize("text", [
    "#introduction #introvert", "#introduction Rin #introvert Rin #introduction",
    "Rin #introvert, Rin #introduction.", "Rin#introvert.",
])
@pytest.mark.parametrize("empty", [False, True])
def test_marker_prefix_words_remain_literal(
    text: str, empty: bool, forms: dict[str, list[ConceptReference]],
) -> None:
    parts = link_text(text, {} if empty else forms, source="owner")
    assert surface(parts) == text
    assert all(not part.introduce for part in parts if isinstance(part, ConceptReference))


@pytest.mark.parametrize("text", [
    "Unknown #intro", "Unknown#intro!", "#intro, Rin", "Rin; #intro; Rin",
    "Rin. the blonde girl #intro", "Rin\n#intro", "Rin. #intro",
])
@pytest.mark.parametrize("empty", [False, True])
def test_unmatched_complete_markers_have_original_offsets(
    text: str, empty: bool, forms: dict[str, list[ConceptReference]],
) -> None:
    with pytest.raises(ValueError, match=rf"owner: unit 4, offset {text.index('#intro') + 10}"):
        link_text(text, {} if empty else forms, source="owner", unit_index=4, offset=10)


@pytest.mark.parametrize("text", ["Rin #intro!", "Rin#intro,", "Rin\t#intro."])
def test_complete_markers_and_name_escape(
    text: str, forms: dict[str, list[ConceptReference]],
) -> None:
    linked = link_text(text, forms, source="owner")
    assert linked[0].introduce
    assert linked[0].intent.value == "auto"
    assert surface(link_text("\\" + text, forms, source="owner")) == text


@pytest.mark.parametrize("text,expected,introduced", [
    (r"\Rin #intro", "Rin #intro", False),
    (r"\\Rin #intro", "\\Rin", True),
    (r"\\\Rin #intro", "\\Rin #intro", False),
    (r"\#intro", "#intro", False),
    (r"\\\#intro", "\\#intro", False),
    (r"\unrelated", r"\unrelated", False),
])
def test_escape_parity_preserves_unrelated_slashes(
    text: str, expected: str, introduced: bool, forms: dict[str, list[ConceptReference]],
) -> None:
    parts = link_text(text, forms, source="owner")
    assert surface(parts) == expected
    assert any(p.introduce for p in parts if isinstance(p, ConceptReference)) is introduced


def test_even_marker_escape_run_does_not_suppress_unmatched_marker(
    forms: dict[str, list[ConceptReference]],
) -> None:
    with pytest.raises(ValueError, match="unmatched #intro"):
        link_text(r"\\#intro", forms, source="owner")


@pytest.mark.parametrize("code", [
    "`Rin #intro`", "``Rin ` #intro``", "```python\nRin #intro\n\n> [!npc] host\n```",
    "~~~\nRin #intro\n~~~", "```\nRin #intro", "`Rin\n\n#intro`",
])
def test_code_regions_are_literal_and_fences_do_not_create_dialog(
    code: str, forms: dict[str, list[ConceptReference]],
) -> None:
    assert surface(link_text(code, forms, source="owner")) == code
    assert not any(p.introduce for p in link_text(code, forms, source="owner")
                   if isinstance(p, ConceptReference))
    assert not DialogHandler.has_mu_blocks(code)


def test_longest_case_sensitive_boundaries_punctuation_and_detached_params(
    forms: dict[str, list[ConceptReference]],
) -> None:
    forms.update({"Rin Senior": [ConceptReference(ref="senior")],
                  "Dr. Rin (Jr.)": [ConceptReference(ref="host_role", params={"form": "formal"})]})
    before = deepcopy(forms)
    text = "  Rin Senior\tmet Dr. Rin (Jr.). Ringo and rin saw the blonde girl.  "
    parts = link_text(text, forms, source="owner")
    refs = [p for p in parts if isinstance(p, ConceptReference)]
    assert [p.ref for p in refs] == ["senior", "host_role"]
    assert refs[1].params == {"form": "formal"}
    assert parts[0] == "  "
    assert parts[-1] == ". Ringo and rin saw the blonde girl.  "
    refs[1].params["form"] = "other"
    assert forms == before


def test_discovery_collapses_corresponding_wrappers_but_not_distinct_bindings() -> None:
    graph = StoryGraph()
    actor = NamedActor(label="rin", name="Rin", registry=graph)
    role = Role(label="host", requirement=Requirement(has_kind=Actor), registry=graph)
    role.set_provider(actor)
    ns = {"host": actor, "host_role": role, "z_role_alias": role}
    before = graph.value_hash()
    table = discover_adoptions(ns)
    assert [ref.ref for ref in table["Rin"]] == ["host_role"]
    assert graph.value_hash() == before
    second = Role(label="peer", requirement=Requirement(has_kind=Actor), registry=graph)
    second.set_provider(actor)
    ns.update({"peer": actor, "peer_role": second})
    with pytest.raises(ValueError, match="owner.*unit 2.*offset 3.*host_role, peer_role"):
        link_text("At Rin", discover_adoptions(ns), source="owner", unit_index=2)
    assert discover_adoptions(dict(reversed(list(ns.items())))) == discover_adoptions(ns)
    # An independently nominated symbol is not the role merely because the
    # provider happens to be shared now; these links may diverge after recast.
    assert len(discover_adoptions({"host": actor, "host_role": role, "memory": actor})["Rin"]) == 2


def test_generic_actor_place_item_and_custom_adoption_are_scoped_and_pure() -> None:
    graph = StoryGraph()
    actor = PersonalNamedActor(name="Rin", anonymous_name="the blonde girl", registry=graph,
                              personal_name=PersonalName(given_name="Rin", family_name="Northstar"))
    place = NamedLocation(name="Market Square", registry=graph)
    item = NamedItem(name="Dawnblade", proper_forms={"inscription": "Dawnblade of the East"},
                     anonymous_name="an old sword", registry=graph)
    outside = NamedItem(name="Outside", registry=graph)
    item.proper_aliases["the blade"] = {"form": "inscription"}
    setting = Setting(
        label="place", requirement=Requirement(has_kind=NamedLocation), registry=graph,
    )
    setting.set_provider(place)
    unbound = Role(label="unbound", requirement=Requirement(has_kind=Actor), registry=graph)
    ns = {"host": actor, "place": place, "place_setting": setting,
          "sword": item, "unbound_role": unbound}
    before = graph.value_hash()
    table = discover_adoptions(ns)
    assert table["Market Square"][0].ref == "place_setting"
    assert table["Dawnblade of the East"][0].params == {"form": "inscription"}
    assert table["the blade"][0].params == {"form": "inscription"}
    assert "the blonde girl" not in table and "Outside" not in table
    link_text("Rin, Market Square, Dawnblade and Outside", table, source="owner")
    assert graph.value_hash() == before
    assert actor.narrator_knowledge == item.narrator_knowledge == outside.narrator_knowledge == {}
    with pytest.raises(ValueError, match="unmatched #intro"):
        link_text("Outside#intro", table, source="owner")


def test_prepared_units_preserve_custom_types_styles_and_opaque_templates(
    forms: dict[str, list[ConceptReference]],
) -> None:
    units = [CustomNarration(text="Rin", style_dict={"color": "red"}),
             DialogMuBlock(label="host_role", dialog_class="npc.happy", text="Rin#intro"),
             MuBlock(template="{{ 'Rin#intro' }}"), MuBlock(text="Rin {{ untouched }} #intro")]
    before = [unit.unstructure() for unit in units]
    prepared = prepare_prose(units, forms, source="owner")
    assert type(prepared[0]) is CustomNarration
    assert prepared[0].style_dict == {"color": "red"}
    assert prepared[0].prepare_fragment().tags == {"custom"}
    assert prepared[1:] == units[1:]
    assert [unit.unstructure() for unit in units] == before


def test_raw_parser_keeps_speech_opaque_and_reports_narration_offset(
    forms: dict[str, list[ConceptReference]],
) -> None:
    text = "Rin waits.\n\n> [!npc.happy] host_role\n> Rin #intro.\n\nUnknown #intro!"
    with pytest.raises(ValueError, match=rf"offset {text.rindex('#intro')}"):
        prepare_prose([MuBlock(text=text)], forms, source="owner")
    prepared = prepare_prose([MuBlock(text=text.replace("Unknown #intro!", "Rin#intro!"),
                                    style_dict={"color": "blue"})], forms, source="owner")
    assert len(prepared) == 3
    assert prepared[1].text == "Rin #intro."
    assert prepared[1].dialog_class == "npc.happy"
    assert prepared[1].style_dict == {"color": "blue"}


def test_reusable_symbolic_link_follows_recast_but_discovery_drops_old_spelling() -> None:
    graph = StoryGraph()
    owner = ProseBlock(registry=graph)
    rin = NamedActor(name="Rin", anonymous_name="the blonde girl", registry=graph)
    beth = NamedActor(name="Beth", anonymous_name="the dark-haired girl", registry=graph)
    role = Role(label="host", requirement=Requirement(has_kind=Actor), registry=graph)
    role.set_provider(rin)
    linked = link_text("Rin", discover_adoptions({"host": rin, "host_role": role}), source="owner")
    role.set_provider(beth)
    ctx = PhaseCtx(graph=graph, cursor_id=owner.uid, current_phase=ResolutionPhase.JOURNAL)
    ctx.local_authorities.append(naming_dispatch)
    ctx._ns_cache[owner.uid] = {"host": beth, "host_role": role,
                               "naming_defaults": {"NamedConcept": "concealed"}}
    before = graph.value_hash()
    assert NamingOperations(ctx).realize(linked) == "the dark-haired girl"
    table = discover_adoptions(ctx.get_ns(owner))
    assert "Beth" in table and "Rin" not in table
    assert graph.value_hash() == before
    assert beth.narrator_knowledge == {}
    with pytest.raises(ValueError, match="unmatched #intro"):
        link_text("Rin#intro", table, source="owner")


def test_form_parameters_reach_auto_policy_before_explicit_introduction() -> None:
    graph = StoryGraph()
    owner = ProseBlock(registry=graph)
    actor = PersonalNamedActor(
        name="Rin", anonymous_name="the blonde girl", registry=graph,
        personal_name=PersonalName(given_name="Rin", family_name="Northstar", title="Ms.",
                                   aliases={"Starlight"}),
    )
    ctx = PhaseCtx(graph=graph, cursor_id=owner.uid, current_phase=ResolutionPhase.JOURNAL)
    ctx.local_authorities.append(naming_dispatch)
    ctx._ns_cache[owner.uid] = {"host": actor, "naming_defaults": {"NamedConcept": "concealed"}}
    before = graph.value_hash()
    parts = link_text("Ms. Northstar / Starlight #intro / Ms. Northstar",
                      discover_adoptions(ctx.get_ns(owner)), source="owner")
    assert graph.value_hash() == before
    assert [p.params for p in parts if isinstance(p, ConceptReference)] == [
        {"form": "formal"}, {"form": "alias:Starlight"}, {"form": "formal"},
    ]
    assert NamingOperations(ctx).realize(parts, disclose=True) == (
        "the blonde girl / Starlight / Ms. Northstar"
    )
    assert actor.peek_knowledge().state == "IDENTIFIED"
    assert actor.name == "Rin"


def test_eligible_name_cannot_cross_a_literal_code_region(
    forms: dict[str, list[ConceptReference]],
) -> None:
    forms["Rin`code`"] = [ConceptReference(ref="other")]
    parts = link_text("Rin`code`", forms, source="owner")
    assert parts[0].ref == "host_role"
    assert parts[1] == "`code`"


def test_speaker_marker_stays_an_exact_symbol_and_never_discloses() -> None:
    graph = StoryGraph()
    owner = ProseBlock(registry=graph)
    actor = NamedActor(name="Rin", registry=graph)
    ctx = PhaseCtx(graph=graph, cursor_id=owner.uid, current_phase=ResolutionPhase.JOURNAL)
    ctx._ns_cache[owner.uid] = {"host": actor}
    operations = NamingOperations(ctx)
    before = graph.value_hash()
    units = prepare_prose([MuBlock(text="> [!npc] host #intro\n> Rin#intro")],
                          discover_adoptions(ctx.get_ns(owner)), source="owner")
    assert units[0].label == "host #intro" and units[0].text == "Rin#intro"
    with pytest.raises(KeyError, match="host #intro"):
        DialogHandler.render(units, ns=ctx.get_ns(owner), ctx=ctx,
                             speaker_resolver=operations.speaker)
    assert graph.value_hash() == before


def test_custom_adoption_and_nominal_policy_keep_identification_distinct_from_wording() -> None:
    graph = StoryGraph()
    owner = ProseBlock(registry=graph)
    relic = QuietRelic(name="Crown", anonymous_name="an unmarked relic", registry=graph,
                       proper_forms={"inscription": "the lost crown"})
    ctx = PhaseCtx(graph=graph, cursor_id=owner.uid, current_phase=ResolutionPhase.JOURNAL)
    ctx.local_authorities.append(naming_dispatch)
    ctx._ns_cache[owner.uid] = {"relic": relic, "naming_defaults": {"NamedConcept": "concealed"}}
    before = graph.value_hash()
    table = discover_adoptions(ctx.get_ns(owner))
    parts = link_text(
        "Unmarked Relic / Unmarked Relic #intro / Unmarked Relic", table, source="owner",
    )
    assert "Crown" not in table
    assert graph.value_hash() == before
    assert NamingOperations(ctx).realize(parts, disclose=True) == (
        "an unmarked relic / the lost crown / an unmarked relic"
    )
    assert relic.peek_knowledge().state == "IDENTIFIED"


def test_inline_triple_backticks_do_not_swallow_later_narration(
    forms: dict[str, list[ConceptReference]],
) -> None:
    parts = link_text("```Rin #intro``` then Rin#intro.", forms, source="owner")
    assert parts[0] == "```Rin #intro``` then "
    assert parts[1].introduce
    assert parts[2] == "."
