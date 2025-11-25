import pydantic

from pydantic import Field, model_validator, ConfigDict, field_validator

from tangl.type_hints import UniqueLabel, Tags, Strings
from tangl.entity import BaseScriptItem
from tangl.entity.mixins import AvailabilityHandler, EffectHandler
from tangl.story.scene.script_models import SceneScript, BlockScript, ActionScript

class EventScriptMixin(pydantic.BaseModel):
    # this stuff can just all go into the regular script defs, I think
    conditions: Strings = Field(default_factory=list,
                                validation_alias=pydantic.AliasChoices('conditions', 'if'))
    effects: Strings = Field(default_factory=list,
                             validation_alias=pydantic.AliasChoices('effects', 'do'))

    reqs: Tags = Field(default_factory=set)  # adds condition `player.has_tags(*x)`
    lose: Tags = Field(default_factory=set)  # adds effect `player.discard_tags(*x)`
    gain: Tags = Field(default_factory=set)  # adds effect `player.add_tags(*x)`

    # @field_validator('reqs', 'lose', 'gain')
    # @classmethod
    # def _convert_to_set(cls, data):
    #     return set(data)

    # Relevant for menu-able items, scenes and blocks in particular
    indicator_text: str = None  # appended to dynamic menu text if avail
    action_text: str = None     # action in dynamic menu if avail

    # Only relevant for sandbox events w loc and independent actors
    who: str = None    # adds condition `Actor x.avail()`, modifiers 'private', 'charmed' for ASFA
    where: str = None  # adds condition `Loc x.avail()`

    @AvailabilityHandler.strategy
    def _include_who(self):
        res = []
        if self.who:
            who, modifier = self.who.split()
            res.append( f"{who}.avail()" )
            # this is specific to asfa
            if modifier in ['private', 'charmed']:
                res.append( f"{who}.{modifier}()")

    @AvailabilityHandler.strategy
    def _include_where(self):
        if self.where:
            return [ f"{self.where}.avail()" ]

    @AvailabilityHandler.strategy
    def _include_requires(self):
        if self.reqs:
            return [ f"player.has_tags(*{list(self.reqs)})" ]

    @EffectHandler.strategy
    def _include_gains(self):
        if self.gain:
            return [ f"player.add_tags(*{list(self.gain)})" ]

    @EffectHandler.strategy
    def _include_loss(self):
        if self.gain:
            return [ f"player.discard_tags(*{list(self.lose)})" ]


class SandboxActionScript(EventScriptMixin, ActionScript):
    # regular script def I think
    successor_ref: str = Field(
        default="return",  # send logic back to loc
        validation_alias=pydantic.AliasChoices('successor_ref', 'target_node', 'go'))

class SandboxBlockScript(EventScriptMixin, BlockScript):

    actions: list[SandboxActionScript] = None
    continues: list[SandboxActionScript] = None
    redirects: list[SandboxActionScript] = None

class SandboxEventScript(EventScriptMixin, SceneScript):

    blocks: dict[str, SandboxBlockScript] = None


class SandboxEventGroupScript(EventScriptMixin, BaseScriptItem):

    events: dict[str, SandboxEventScript]


