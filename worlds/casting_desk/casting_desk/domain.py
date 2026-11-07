"""World-owned catalog, finite applicant slots and explicit UPDATE completion."""
from __future__ import annotations

from pathlib import Path
from typing import cast

from pydantic import Field
import yaml

from tangl.core import BehaviorRegistry, TokenCatalog
from tangl.mechanics.demographics import (
    GenerationReceipt, GenerationRequest, HasDemographics, NameBank,
    complete_generation, name_catalog,
)
from tangl.prose.naming import (
    PersonalNamedActor, ProseBlock, get_authorities as naming_authorities,
)
from tangl.vm.runtime.frame import PhaseCtx


# Loading this world adopts its own authored banks and nothing else: no national
# pack is registered. Each resource file holds one authored NameBank.
BANK_DIR = Path(__file__).resolve().parents[1] / "resources" / "names"
NAMES = name_catalog(overrides=tuple(
    NameBank.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    for path in sorted(BANK_DIR.glob("*.yaml"))
))


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
    """An explicit UPDATE entry for one scene-bound applicant."""


desk_dispatch = BehaviorRegistry(label="casting_desk.update")


@desk_dispatch.register(task="apply_update", wants_caller_kind=CompleteApplicant)
def complete_applicant(*, caller: CompleteApplicant, ctx: PhaseCtx, **_kwargs: object) -> None:
    applicant = cast(Applicant, ctx.get_ns()["applicant"])
    if applicant.generation_receipt is not None:
        return
    (
        applicant.personal_name, applicant.demographic, applicant.generation_receipt,
    ) = complete_generation(
        applicant.generation_request, personal_name=applicant.personal_name,
        demographic=applicant.demographic, receipt=applicant.generation_receipt, ctx=ctx,
    )


def get_authorities() -> list[BehaviorRegistry]:
    return [*naming_authorities(), desk_dispatch]
