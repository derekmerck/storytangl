from __future__ import annotations

import logging
from typing import Any, Optional, Literal, ClassVar, Type
from uuid import UUID

import pydantic
from pydantic import Field, model_validator, ConfigDict, field_validator

from tangl.type_hints import UniqueLabel, Tag, ClassName, StringMap
from tangl.core import Entity
from tangl.ir.core_ir import BaseScriptItem
from tangl.ir.media_ir.media_script_model import MediaItemScript
from .actor_script_models import RoleScript
from .location_script_models import SettingScript
from .asset_script_models import AssetsScript


logger = logging.getLogger(__name__)


def _role_spec_missing_references(spec: dict[str, Any]) -> bool:
    return not any(
        spec.get(field)
        for field in ('actor_ref', 'actor_template', 'actor_template_ref')
    )


def _expand_role_shorthands(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, list):
        result: dict[UniqueLabel, Any] = {}
        for item in value:
            if isinstance(item, str):
                result[item] = {'actor_ref': item}
            elif isinstance(item, dict):
                label = item.get('label')
                if not label:
                    raise ValueError(f"Role in list must have 'label': {item}")
                result[label] = dict(item)
            else:
                raise ValueError(f"Invalid role list entry: {item}")
        return result

    if isinstance(value, dict):
        result: dict[UniqueLabel, Any] = {}
        for label, spec in value.items():
            if spec is None:
                result[label] = {'actor_ref': label}
            elif isinstance(spec, str):
                result[label] = {'actor_ref': spec}
            elif isinstance(spec, RoleScript):
                result[label] = spec
            elif isinstance(spec, dict):
                normalized = dict(spec)
                if _role_spec_missing_references(normalized):
                    logger.warning(
                        "Role '%s' has no actor_ref/template/template_ref, "
                        "inferring actor_ref='%s'", label, label,
                    )
                    normalized.setdefault('actor_ref', label)
                result[label] = normalized
            else:
                raise ValueError(f"Invalid role spec for '{label}': {spec}")
        return result

    return value


def _expand_setting_shorthands(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, list):
        result: dict[UniqueLabel, Any] = {}
        for item in value:
            if isinstance(item, str):
                result[item] = {'location_ref': item}
            elif isinstance(item, dict):
                label = item.get('label')
                if not label:
                    raise ValueError(f"Setting in list must have 'label': {item}")
                result[label] = dict(item)
            else:
                raise ValueError(f"Invalid setting list entry: {item}")
        return result

    if isinstance(value, dict):
        result: dict[UniqueLabel, Any] = {}
        for label, spec in value.items():
            if spec is None:
                result[label] = {'location_ref': label}
            elif isinstance(spec, str):
                result[label] = {'location_ref': spec}
            elif isinstance(spec, SettingScript):
                result[label] = spec
            elif isinstance(spec, dict):
                normalized = dict(spec)
                if not any(
                    normalized.get(field)
                    for field in (
                        'location_ref',
                        'location_template',
                        'location_template_ref',
                    )
                ):
                    logger.warning(
                        "Setting '%s' has no location_ref/template/template_ref, "
                        "inferring location_ref='%s'", label, label,
                    )
                    normalized.setdefault('location_ref', label)
                result[label] = normalized
            else:
                raise ValueError(f"Invalid setting spec for '{label}': {spec}")
        return result

    return value


class ActionScript(BaseScriptItem):
    """
    Defines an action within a story, including any text associated with the action,
    the conditions under which the action is available, and its effects.

    An action represents a choice available to the user or an automatic progression in the story.

    Attributes:
        text (str, optional): The text presented to the user for this action. Required if trigger is `choice`.
        target_node (str): A unique reference to the succeeding story node. Can be a block label in the same scene, a scene label, or a scene/block path.
        trigger (str, optional): The condition that triggers this action. Can be 'redirect' (jump before event), 'continue' (automatic jump after event), or 'choice' (await user selection).
        conditions (list[str], optional): Conditions that must be met for this action to be available.
        effects (list[str], optional): Effects that occur as a result of taking this action.
    """

    @classmethod
    def get_default_obj_cls(cls) -> Type[Entity]:
        from tangl.story.episode import Action
        return Action

    text: Optional[str] = Field(
        None,
        description="The narrative text associated with this choice or action."
    )
    successor: UniqueLabel | UUID = Field(
        ...,
        description="Unique reference to the next node in the story script.  Can be a block label in the same scene, a scene label, a scene/block path, or a uid if the uid of the target is known."
    )
    activation: Optional[Literal["first", "last"]] = Field(
        None,
        alias="trigger",
        description="The type of trigger for this action. Can be 'first' (jump before event), 'last' (automatic jump after event), or None (default, await user selection)."
    )

    @model_validator(mode="before")
    @classmethod
    def _alias_successor_ref_to_target_node(cls, data):
        if 'successor_ref' in data:
            data['target_ref'] = data.pop('successor_ref')
        return data

    @model_validator(mode='after')
    def _check_choice_has_text(self):
        if self.activation not in ["first", "last"] and not self.text:
            raise ValueError(f'Action requires text or automatic trigger ({self.activation})')
        return self

    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "text": "Open the door",
                "target_ref": "node123",
                "conditions": ["'key' in player.inv"],
                "effects": ["door_opened = True"]
            }
        }
    )


class BlockScript(BaseScriptItem):

    @classmethod
    def get_default_obj_cls(cls) -> Type[Entity]:
        # Keep this import out of the main scope
        from tangl.story.episode import Block
        return Block

    media: list[MediaItemScript] | None = None

    actions: list[ActionScript] = Field(None, description="Actions available to the user at the end of this block.", json_schema_extra={"visit_field": True})
    continues: list[ActionScript] = Field(None, description="Continuations to a next block.", json_schema_extra={"visit_field": True})
    redirects: list[ActionScript] = Field(None, description="Automatic redirections to a different block.", json_schema_extra={"visit_field": True})
    templates: Optional[dict[UniqueLabel, dict[str, Any]]] = Field(
        None,
        description="Templates available only within this block.",
    )
    roles: list[RoleScript] | dict[UniqueLabel, RoleScript] = Field(
        None,
        description="Roles scoped to this block, provided as a list or mapping.", json_schema_extra={"visit_field": True}
    )
    settings: list[SettingScript] | dict[UniqueLabel, SettingScript] = Field(
        None,
        description="Settings scoped to this block, provided as a list or mapping.", json_schema_extra={"visit_field": True}
    )

    @pydantic.field_validator('redirects', mode='before')
    @classmethod
    def _set_enter_trigger(cls, data):
        for d in data:
            d.setdefault('trigger', 'first')
        return data

    @pydantic.field_validator('continues', mode='before')
    @classmethod
    def _set_exit_trigger(cls, data):
        for d in data:
            try:
                d.setdefault('trigger', 'last')
            except AttributeError:
                print( d )
                raise
        return data

    @pydantic.field_validator('roles', mode='before')
    @classmethod
    def _expand_role_shorthands(cls, value):
        return _expand_role_shorthands(value)

    @pydantic.field_validator('settings', mode='before')
    @classmethod
    def _expand_setting_shorthands(cls, value):
        return _expand_setting_shorthands(value)


class MenuBlockScript(BlockScript):
    wants_tags: list[Tag] = Field(None, description="Required tags on dynamically assigned menu items.")
    wants_cls: ClassName = Field(None, description="Required class for dynamically assigned menu items.")

    # todo: at least 1 of


class SceneScript(BaseScriptItem):

    @classmethod
    def get_default_obj_cls(cls) -> Type[Entity]:
        # Keep this import out of the main scope
        from tangl.story.episode import Scene
        return Scene

    text: Optional[str] = Field(None, alias="title", description="The scene title.")

    # todo: How do we inject other block types like menus, challenges (games) and activities (task)??  using discriminator fields?
    blocks: list[BlockScript] | dict[UniqueLabel, BlockScript] = Field(..., description="Block objects in label-keyed map or list form.", json_schema_extra={"visit_field": True})
    roles: list[RoleScript] | dict[UniqueLabel, RoleScript] = Field(None, description="Roles associated with this scene, provides scene-specific aliases for cast actors, in label-keyed map or list form.", json_schema_extra={"visit_field": True})
    settings: list[SettingScript] | dict[UniqueLabel, SettingScript] = Field(None, description="Settings associated with this scene, provides scene-specific aliases for locations, in label-keyed map or list form.", json_schema_extra={"visit_field": True})
    assets: list[AssetsScript] = Field(None, description="A list of asset types and items associated with the scene.")
    templates: Optional[dict[UniqueLabel, dict[str, Any]]] = Field(
        None,
        description="Templates available to blocks in this scene.",
    )

    # @field_validator('blocks', 'roles', 'settings', mode="before")
    # @classmethod
    # def __set_label_from_key(cls, value: dict[UniqueLabel, StringMap]) -> dict[UniqueLabel, StringMap]:
    #     return cls._set_label_from_key(value)

    @pydantic.field_validator('roles', mode='before')
    @classmethod
    def _expand_role_shorthands(cls, value):
        return _expand_role_shorthands(value)

    @pydantic.field_validator('settings', mode='before')
    @classmethod
    def _expand_setting_shorthands(cls, value):
        return _expand_setting_shorthands(value)




