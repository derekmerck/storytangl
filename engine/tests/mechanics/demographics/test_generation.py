"""Explicit UPDATE generation, pre-event re-execution and committed-state replay."""
from __future__ import annotations
import os
from pathlib import Path
from random import Random
import subprocess
import sys
from uuid import uuid4
import pytest
from tangl.core import EntityTemplate, Selector
from tangl.lang.personal_name import PersonalName
from tangl.mechanics.demographics import (
    DemographicData, GenerationRequest, NameBank, complete_generation, Country, Region, Origin,
)
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.story import World
from tangl.vm import Ledger, ResolutionPhase
from tangl.vm.runtime.frame import PhaseCtx
from tangl.vm.replay import CheckpointRecord, Patch, get_replay_engine
from pytest_helpers.demographic_generation import RequestedActor, bootstrap, observed

def session(
    request: GenerationRequest, name: PersonalName | None = None,
    facts: DemographicData | None = None,
) -> tuple[World, Ledger]:
    world=bootstrap("generation_"+uuid4().hex)
    world.templates.add(EntityTemplate.from_data({
        "kind":RequestedActor,"label":"cast","personal_name":name,
        "demographic":facts or DemographicData(),"generation_request":request,
    }))
    graph=world.create_story("generation").graph
    return world, Ledger.from_graph(graph,entry_id=graph.initial_cursor_id)

def subject(ledger: Ledger) -> RequestedActor:
    return ledger.graph.find_one(Selector(label="cast",has_kind=RequestedActor))

def advance(ledger: Ledger) -> None:
    ledger.resolve_choice(next(ledger.cursor.edges_out()).uid)

def test_update_reexecution_diff_replay_rename_and_fresh_restore(tmp_path: Path) -> None:
    world,ledger=session(GenerationRequest(
        facts={"gender","age_range"},name_parts={"given_name":True,"family_name":True},
        bank="fra",form="female",
    ),PersonalName(given_name="Pinned",title="Dr.",aliases={"Alias"},family_name_first=True))
    saved=Json.serialize(ledger.unstructure())
    before=subject(ledger).uid
    advance(ledger)
    first=subject(ledger)
    assert first.uid==before and first.personal_name.given_name=="Pinned"
    assert first.personal_name.title=="Dr." and first.personal_name.aliases=={"Alias"}
    assert first.personal_name.family_name_first
    assert first.generation_receipt.bank is NameBank.get_instance("fra")
    assert first.generation_receipt.revision=="sample-v1"
    assert first.generation_receipt.generated==["gender","age_range","family_name"]
    assert first.demographic.country is None
    state=first.unstructure()
    rng=observed[-1]
    again=Ledger.structure(Json.deserialize(saved))
    advance(again)
    assert subject(again).unstructure()==state
    assert observed[-1]==rng
    assert again.graph.value_hash()==ledger.graph.value_hash()
    engine=get_replay_engine(ledger.replay_algorithm_id)
    checkpoint=next(Selector(has_kind=CheckpointRecord).filter(ledger.output_stream))
    replayed=engine.restore_checkpoint(checkpoint)
    for patch in Selector(has_kind=Patch).filter(ledger.output_stream):
        replayed=engine.apply_delta(graph=replayed,delta=patch)
    assert replayed.value_hash()==ledger.graph.value_hash()
    original_receipt=first.generation_receipt.unstructure()
    first.personal_name.family_name=None
    first.personal_name.given_name="Renamed"
    advance(ledger); advance(ledger)
    assert subject(ledger).personal_name.given_name=="Renamed"
    assert subject(ledger).personal_name.family_name is None
    assert subject(ledger).generation_receipt.unstructure()==original_receipt
    assert observed[-1][0]==observed[-1][1]
    path=tmp_path/"ledger.json"; path.write_text(Json.serialize(ledger.unstructure()))
    script='''
import sys
from pathlib import Path
from unittest.mock import patch
from tangl.vm import Ledger
from tangl.persistence.serializers import JsonSerializationHandler as Json
from tangl.core import Selector
from tangl.mechanics.demographics import NameBank
from pytest_helpers.demographic_generation import bootstrap, RequestedActor, observed
with patch('tangl.mechanics.demographics.generation._sample_part',side_effect=AssertionError('sampled')):
    bootstrap(sys.argv[2])
    ledger=Ledger.structure(Json.deserialize(Path(sys.argv[1]).read_text()))
    actor=ledger.graph.find_one(Selector(label='cast',has_kind=RequestedActor))
    assert actor.personal_name.given_name=='Renamed'
    assert actor.personal_name.family_name is None
    assert actor.generation_receipt.bank is NameBank.get_instance('fra')
    for _ in range(2): ledger.resolve_choice(next(ledger.cursor.edges_out()).uid)
    assert observed[-1][0]==observed[-1][1]
'''
    env={**os.environ,"PYTHONPATH":os.pathsep.join(filter(None,(str(Path(__file__).resolve().parents[2]),os.environ.get("PYTHONPATH"))))}
    result=subprocess.run([sys.executable,"-c",script,str(path),world.label],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr

def test_pinned_names_do_not_choose_unused_mixture_or_draw() -> None:
    world,ledger=session(GenerationRequest(name_parts={"given_name":True,"family_name":True},
        origin=Origin(label="shared",banks={"fra":1,"jpn":1}),form="female"),
        PersonalName(given_name="Pinned",family_name="Authored"))
    advance(ledger)
    assert observed[-1][0]==observed[-1][1]
    assert subject(ledger).generation_receipt.bank is None

@pytest.mark.parametrize("spec,facts",[
    (GenerationRequest(name_parts={"given_name":True},bank="missing",form="female"),DemographicData()),
    (GenerationRequest(name_parts={"given_name":True},bank="fra",form="missing"),DemographicData()),
])
def test_invalid_references_leave_values_and_rng_unchanged(
    spec: GenerationRequest, facts: DemographicData,
) -> None:
    world,ledger=session(spec,facts=facts)
    actor=subject(ledger)
    ctx=PhaseCtx(graph=ledger.graph,cursor_id=ledger.cursor_id,current_phase=ResolutionPhase.UPDATE,random=Random(7))
    before=ctx.get_random().getstate()
    with pytest.raises((ValueError,LookupError)):
        complete_generation(spec,personal_name=None,demographic=facts,receipt=None,ctx=ctx)
    assert ctx.get_random().getstate()==before
    assert actor.generation_receipt is None

def test_mononym_recipe_and_authored_absence_do_not_force_other_dimensions() -> None:
    from tangl.mechanics.demographics import NameForm, NamePart, NamePool, name_catalog
    spec=GenerationRequest(name_parts={"given_name":True,"family_name":True},bank="sprite",form="free")
    world,ledger=session(spec)
    sprite=NameBank(label="sprite_"+uuid4().hex,selection_key="sprite",revision="sprite-v1",
        forms={"free":NameForm(given=NamePart(pool=NamePool(candidates=["Cookie"])))})
    world.assets.names=name_catalog(world.assets.names,overrides=(sprite,))
    advance(ledger)
    actor=subject(ledger)
    assert actor.personal_name.full_name()=="Cookie"
    assert actor.personal_name.family_name is None
    assert actor.demographic.gender is actor.demographic.country is actor.demographic.age_range is None
    assert actor.generation_receipt.generated==["given_name"]
    assert actor.generation_receipt.revision=="sprite-v1"
    assert actor.generation_receipt.bank is sprite

def test_constraints_and_phase_are_validated_before_draws() -> None:
    world,ledger=session(GenerationRequest())
    ctx=PhaseCtx(graph=ledger.graph,cursor_id=ledger.cursor_id,current_phase=ResolutionPhase.UPDATE,random=Random(7))
    profile=DemographicData(country=Country.get_instance("fra"),region=Region.get_instance("asia"))
    before=ctx.get_random().getstate()
    with pytest.raises(ValueError,match="contradict"):
        complete_generation(GenerationRequest(facts={"gender"}),personal_name=None,demographic=profile,receipt=None,ctx=ctx)
    assert ctx.get_random().getstate()==before
    ctx.current_phase=ResolutionPhase.PLANNING
    with pytest.raises(ValueError,match="UPDATE"):
        complete_generation(GenerationRequest(facts={"gender"}),personal_name=None,demographic=DemographicData(),receipt=None,ctx=ctx)

def test_age_aliases_are_unique_and_pinned_fields_have_zero_budget() -> None:
    from tangl.lang.age_range import AgeRange
    from tangl.lang.gens import Gens
    from tangl.mechanics.demographics import Subtype, load_pack, register_pack
    register_pack(load_pack("sample"))
    world,ledger=session(GenerationRequest(facts={"region","country","subtype","gender","age_range"}),
        facts=DemographicData(region=Region.get_instance("west_europe"),country=Country.get_instance("fra"),
            subtype=Subtype.get_instance("european"),gender=Gens.X_,age_range=AgeRange.ADULT))
    advance(ledger)
    assert observed[-1][0]==observed[-1][1]
    assert subject(ledger).generation_receipt.generated==[]
    class Capture(Random):
        def choice(self,values):
            assert values==list(AgeRange)
            assert len(values)==len(set(values))
            return values[0]
    actor=subject(ledger)
    ctx=PhaseCtx(graph=ledger.graph,cursor_id=ledger.cursor_id,current_phase=ResolutionPhase.UPDATE,random=Capture())
    result=complete_generation(GenerationRequest(facts={"age_range"}),personal_name=None,
        demographic=DemographicData(),receipt=None,ctx=ctx)
    assert result[1].age_range is list(AgeRange)[0]

def test_explicit_none_family_is_preserved_while_unset_given_is_filled() -> None:
    world,ledger=session(GenerationRequest(name_parts={"given_name":True,"family_name":False},bank="fra",form="female"),
        PersonalName(family_name=None,title="",aliases={"Pinned alias"}))
    advance(ledger)
    actor=subject(ledger)
    assert actor.personal_name.family_name is None
    assert actor.personal_name.given_name
    assert actor.personal_name.aliases=={"Pinned alias"}
    assert actor.generation_receipt.generated==["given_name"]

def test_requested_country_and_subtype_use_stable_population_candidates() -> None:
    from tangl.mechanics.demographics import load_pack, register_pack
    register_pack(load_pack("sample"))
    spec=GenerationRequest(facts={"country","subtype"})
    world,ledger=session(spec,facts=DemographicData(region=Region.get_instance("west_europe")))
    actor=subject(ledger)
    class Capture(Random):
        def choices(self,values,weights=None,**kwargs):
            assert [value.label for value in values]==sorted(value.label for value in values)
            return super().choices(values,weights=weights,**kwargs)
    ctx=PhaseCtx(graph=ledger.graph,cursor_id=ledger.cursor_id,current_phase=ResolutionPhase.UPDATE,random=Capture(7))
    name,facts,receipt=complete_generation(spec,personal_name=None,demographic=actor.demographic,receipt=None,ctx=ctx)
    assert facts.country.region is facts.region
    assert facts.subtype in facts.country.eth_mix
    assert name is None and facts.gender is facts.age_range is None
    assert receipt.generated==["country","subtype"]

def test_fully_authored_name_needs_no_unused_bank_policy() -> None:
    world,ledger=session(GenerationRequest(name_parts={"given_name":True,"family_name":True}),
        PersonalName(given_name="All",family_name="Authored"))
    advance(ledger)
    assert observed[-1][0]==observed[-1][1]
    assert subject(ledger).generation_receipt.generated==[]
