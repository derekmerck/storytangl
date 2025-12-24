from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING, Type

from pydantic import Field, model_validator

from tangl.type_hints import Expr, UniqueLabel, StringMap
from tangl.core import Entity
from tangl.ir.core_ir import BaseScriptItem
from .actor_script_models import ActorScript
from .asset_script_models import AssetsScript


class LocationScript(BaseScriptItem):

    @classmethod
    def get_default_obj_cls(cls) -> Type[Entity]:
        # Keep this import out of the main scope
        from tangl.story.concepts.location import Location
        return Location

    assets: list[AssetsScript] = None   # assets associated with the loc
    extras: list[ActorScript] = None    # extras associated with the loc



class SettingScript(BaseScriptItem):

    @classmethod
    def get_default_obj_cls(cls) -> Type[Entity]:
        # Keep this import out of the main scope
        from tangl.story.concepts.location import Setting
        return Setting

    location_template: Optional[LocationScript] = Field(None, json_schema_extra={'child_script': True})
    location_ref: Optional[UniqueLabel] = None
    location_template_ref: Optional[UniqueLabel] = Field(
        None,
        description="Reference to template in :attr:`World.template_registry`.",
    )
    location_overrides: Optional[dict[str, Any]] = Field(
        None,
        description="Overrides applied when instantiating from a template reference.",
    )
    location_criteria: Optional[StringMap] = None
    location_conditions: Optional[list[Expr]] = None
    requirement_policy: Optional[str] = Field(
        None,
        description="Provisioning policy such as ``EXISTING`` or ``CREATE``.",
    )

    assets: list[AssetsScript] = None   # assets associated with the setting
    extras: list[ActorScript] = None   # extras associated with the setting

    @model_validator(mode="after")
    def _validate_reference_exclusivity(self) -> SettingScript:
        """Ensure mutually exclusive location template sources."""

        if self.location_template is not None and self.location_template_ref is not None:
            msg = (
                f"Setting '{self.label}': Cannot combine inline template and template reference"
            )
            raise ValueError(msg)

        return self

