import pydantic
from typing import Optional, Literal, Type
from uuid import UUID

from pydantic import Field, model_validator, ConfigDict

from tangl.type_hints import UniqueLabel
from tangl.entity import BaseScriptItem, SingletonEntity
from tangl.media import MediaItemScript
from ..asset import AssetScript
from ..actor import RoleScript
from ..place import LocationScript

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
    successor_ref: UniqueLabel | UUID = Field(
        ...,
        alias="target_ref",
        description="Unique reference to the next node in the story script.  Can be a block label in the same scene, a scene label, a scene/block path, or a uid if the uid of the target is known."
    )
    activation: Optional[Literal["enter", "exit"]] = Field(
        None,
        alias="trigger",
        description="The type of trigger for this action. Can be 'enter' (jump before event), 'exit' (automatic jump after event), or None (default, await user selection)."
    )

    @model_validator(mode="before")
    @classmethod
    def _alias_successor_ref_to_target_node(cls, data):
        if 'successor_ref' in data:
            data['target_ref'] = data.pop('successor_ref')
        return data

    @model_validator(mode='after')
    def _check_choice_has_text(self):
        if self.activation not in ["enter", "exit"] and not self.text:
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

    media: list[MediaItemScript] = None

    actions: list[ActionScript] = None
    continues: list[ActionScript] = None
    redirects: list[ActionScript] = None

    @pydantic.field_validator('redirects', mode='before')
    @classmethod
    def _set_enter_trigger(cls, data):
        for d in data:
            d.setdefault('trigger', 'enter')
        return data

    @pydantic.field_validator('continues', mode='before')
    @classmethod
    def _set_exit_trigger(cls, data):
        for d in data:
            try:
                d.setdefault('trigger', 'exit')
            except AttributeError:
                print( d )
                raise
        return data


class SceneScript(BaseScriptItem):
    text: Optional[str] = Field(None, alias="title")

    blocks: dict[UniqueLabel, BlockScript] = None
    roles: Optional[dict[UniqueLabel, Optional[RoleScript]]] = None
    locations: Optional[dict[UniqueLabel, Optional[LocationScript]]] = None
    assets: Optional[dict[Type[SingletonEntity], dict[UniqueLabel, AssetScript]]] = None

    @pydantic.field_validator('roles', 'locations', mode='after')
    @classmethod
    def _null_roles_and_locs_reference_their_key(cls, data: dict[UniqueLabel, BaseScriptItem]):
        for k, v in data.items():
            if v is None:
                data[k] = RoleScript(actor_ref=k)
        return data

