"""World-owned catalog, finite applicant slots and explicit UPDATE completion."""
from __future__ import annotations

from typing import cast

from pydantic import Field

from tangl.core import BehaviorRegistry, TokenCatalog
from tangl.mechanics.demographics import (
    GenerationReceipt, GenerationRequest, HasDemographics, NameBank, NameForm,
    NamePart, NamePool, complete_generation, load_pack, name_catalog, register_pack,
)
from tangl.prose.naming import (
    PersonalNamedActor, ProseBlock, get_authorities as naming_authorities,
)
from tangl.vm.runtime.frame import PhaseCtx


# Loading this world explicitly adopts the small regular-git sample pack.
# The generic demographics package still loads no definitions on import.
SPRITE_BANK = NameBank(
    label="casting_desk.sprite", selection_key="sprite", revision="casting-desk-v1",
    forms={"plain": NameForm(
        given=NamePart(pool=NamePool(
            candidates=["Cookie", "Pepper", "Clover"], weights=[2, 1, 1],
        )),
        family=NamePart(
            pool=NamePool(candidates=["Winter", "Summer", "Moon"]),
            suffix=NamePool(candidates=["green", "mint", "bloom"]),
        ),
    )},
)
NAMES = name_catalog(register_pack(load_pack("sample")), overrides=(SPRITE_BANK,))


def get_token_catalogs(**_kwargs: object) -> list[TokenCatalog[NameBank]]:
    """Publish this world's explicit offers through the ordinary module seam."""
    return [NAMES]


class Applicant(PersonalNamedActor, HasDemographics):
    """One template-materialized cast slot with the existing name/profile owners."""

    generation_request: GenerationRequest = Field(
        json_schema_extra={"unstructurable": True},
    )
    generation_receipt: GenerationReceipt | None = Field(
        default=None, json_schema_extra={"include": True, "unstructurable": True},
    )


class CompleteApplicant(ProseBlock):
    """An authored entry event, with a reproducible seed for its one applicant."""

    seed: int


desk_dispatch = BehaviorRegistry(label="casting_desk.update")


@desk_dispatch.register(task="apply_update", wants_caller_kind=CompleteApplicant)
def complete_applicant(*, caller: CompleteApplicant, ctx: PhaseCtx, **_kwargs: object) -> None:
    applicant = cast(Applicant, ctx.get_ns()["applicant"])
    if applicant.generation_receipt is not None:
        return
    ctx.get_random().seed(caller.seed)
    (
        applicant.personal_name, applicant.demographic, applicant.generation_receipt,
    ) = complete_generation(
        applicant.generation_request, personal_name=applicant.personal_name,
        demographic=applicant.demographic, receipt=applicant.generation_receipt, ctx=ctx,
    )


def get_authorities() -> list[BehaviorRegistry]:
    return [*naming_authorities(), desk_dispatch]
