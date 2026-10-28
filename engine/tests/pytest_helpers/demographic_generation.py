"""Opt-in UPDATE fixture; actors exist through templates before generation."""
from __future__ import annotations
from pydantic import Field
from tangl.core import BehaviorRegistry, EntityTemplate, Selector
from tangl.mechanics.demographics import (
    DemographicData, GenerationRequest, GenerationReceipt, complete_generation,
)
from tangl.story import Block, World
from tangl.vm.runtime.frame import PhaseCtx
from pytest_helpers.demographic_actor import ProfileActor, NamingAssets
from tangl.mechanics.demographics import load_pack, register_pack
from tangl.prose.naming import get_authorities

class RequestedActor(ProfileActor):
    generation_request: GenerationRequest = Field(json_schema_extra={"unstructurable": True})
    generation_receipt: GenerationReceipt | None = Field(
        default=None, json_schema_extra={"unstructurable": True,"include": True},
    )

observed: list[tuple[object, object]] = []

def fill(*, caller: Block, ctx: PhaseCtx, **_kw: object) -> None:
    if caller.label != "generate":
        return
    actor = ctx.graph.find_one(Selector(label="cast",has_kind=RequestedActor))
    before = ctx.get_random().getstate()
    actor.personal_name, actor.demographic, actor.generation_receipt = complete_generation(
        actor.generation_request, personal_name=actor.personal_name, demographic=actor.demographic,
        receipt=actor.generation_receipt, ctx=ctx,
    )
    observed.append((before,ctx.get_random().getstate()))

def bootstrap(label: str) -> World:
    catalog = register_pack(load_pack("sample"))
    world = World.from_script_data(script_data={
        "label":label,"metadata":{"start_at":"s.start"},
        "scenes":{"s":{"blocks":{
            "start":{"content":"Start","actions":[{"text":"Generate","successor":"generate"}]},
            "generate":{"content":"Done","actions":[{"text":"Return","successor":"start"}]},
        }}},
    },assets=NamingAssets(catalog))
    dispatch = BehaviorRegistry(label=label+".generation")
    dispatch.register(fill,task="apply_update",wants_caller_kind=Block)
    world.extra_authorities.extend([*get_authorities(),dispatch])
    return world
