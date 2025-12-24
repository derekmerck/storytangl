from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING, ClassVar, Type

from pydantic import Field, model_validator

from tangl.type_hints import Expr, UniqueLabel, StringMap
from tangl.core import Entity
from tangl.lang.gens import Gens
from tangl.ir.core_ir import BaseScriptItem
from .asset_script_models import AssetsScript

MediaItemScript = BaseScriptItem

class ActorScript(BaseScriptItem):

    @classmethod
    def get_default_obj_cls(cls) -> Type[Entity]:
        # Keep this import out of the main scope
        from tangl.story.concepts.actor import Actor
        return Actor

    name: Optional[str] = None
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    # at least 1 of name, full name, or first and land
    gender: Optional[Gens] = None

    # todo: consider how to reserve a look, demographics field for mechanics that may not be used?

    assets: list[AssetsScript] = None     # assets associated with the actor

    # look: Optional[LookScript] = None
    # wearables: Optional[list[AssetScript]] = Field(None, alias="outfit")
    # ornaments: Optional[OrnamentationScript] = None

    media: list[MediaItemScript] = None


class RoleScript(BaseScriptItem):

    @classmethod
    def get_templ_cls_hint(cls) -> Type[Entity]:
        # Keep this import out of the main scope
        from tangl.story.concepts.actor import Role
        return Role

    actor_template: Optional[ActorScript] = Field(None, json_schema_extra={'child_script': True})
    actor_ref: Optional[UniqueLabel] = None
    actor_template_ref: Optional[UniqueLabel] = Field(
        None,
        description="Reference to template in :attr:`World.template_registry`.",
    )
    actor_overrides: Optional[dict[str, Any]] = Field(
        None,
        description="Overrides applied when instantiating from a template reference.",
    )
    actor_criteria: Optional[StringMap] = None
    actor_conditions: Optional[list[Expr]] = None
    requirement_policy: Optional[str] = Field(
        None,
        description="Provisioning policy such as ``EXISTING`` or ``CREATE``.",
    )

    assets: list[AssetsScript] = None     # assets associated with the role, titles, gold badge for sherif

    @model_validator(mode="after")
    def _validate_reference_exclusivity(self) -> RoleScript:
        """Ensure mutually exclusive actor template sources."""

        if self.actor_template is not None and self.actor_template_ref is not None:
            msg = (
                f"Role '{self.label}': Cannot combine inline template and template reference"
            )
            raise ValueError(msg)

        return self

# class ExtrasScript ... ?

