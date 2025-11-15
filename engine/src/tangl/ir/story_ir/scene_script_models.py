import pydantic
from typing import Any, Optional, Literal, Type
from uuid import UUID

from pydantic import Field, model_validator, ConfigDict

from tangl.type_hints import UniqueLabel, Tag, ClassName
from tangl.ir.core_ir import BaseScriptItem
from .actor_script_models import RoleScript
from .location_script_models import SettingScript
from .asset_script_models import AssetsScript


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

    obj_cls: ClassName = Field(None, alias='block_cls')
    # todo: suggest known block class descendents in schema but allow any

    # media: list[MediaItemScript] = None

    actions: list[ActionScript] = Field(None, description="Actions available to the user at the end of this block.")
    continues: list[ActionScript] = Field(None, description="Continuations to a next block.")
    redirects: list[ActionScript] = Field(None, description="Automatic redirections to a different block.")
    templates: Optional[dict[UniqueLabel, dict[str, Any]]] = Field(
        None,
        description="Templates available only within this block.",
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


class MenuBlockScript(BlockScript):
    wants_tags: list[Tag] = Field(None, description="Required tags on dynamically assigned menu items.")
    wants_cls: ClassName = Field(None, description="Required class for dynamically assigned menu items.")

    # todo: at least 1 of


class SceneScript(BaseScriptItem):
    text: Optional[str] = Field(None, alias="title", description="The scene title.")

    # todo: How do we inject other block types like menus, challenges (games) and activities (task)??  using discriminator fields?
    blocks: list[BlockScript] | dict[UniqueLabel, BlockScript] = Field(..., description="Block objects in label-keyed map or list form.")
    roles: list[RoleScript] | dict[UniqueLabel, RoleScript] = Field(None, description="Roles associated with this scene, provides scene-specific aliases for cast actors, in label-keyed map or list form.")
    settings: list[SettingScript] | dict[UniqueLabel, SettingScript] = Field(None, description="Settings associated with this scene, provides scene-specific aliases for locations, in label-keyed map or list form.")
    assets: list[AssetsScript] = Field(None, description="A list of asset types and items associated with the scene.")
    templates: Optional[dict[UniqueLabel, dict[str, Any]]] = Field(
        None,
        description="Templates available to blocks in this scene.",
    )

    @pydantic.field_validator('roles', 'settings', mode='after')
    @classmethod
    def _null_roles_and_locs_reference_their_key(cls, data: dict[UniqueLabel, BaseScriptItem]):
        if isinstance(data, dict):
            for k, v in data.items():
                if v is None:
                    data[k] = RoleScript(actor_ref=k)
        return data


