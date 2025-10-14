import logging
from typing import Optional

from pydantic import Field, model_validator, field_validator

from tangl.type_hints import UniqueLabel, StringMap, Identifier, Predicate
from tangl.vm.planning import Dependency
# from tangl.core import DynamicEdge, on_associate, on_disassociate, on_can_associate, on_can_disassociate
# from tangl.story.story_node import StoryNode
# from tangl.core.services import Predicate
# from tangl.core.solver import DependencyEdge
from .location import Location

logger = logging.getLogger(__name__)

class Setting(Dependency[Location]):
    # Scene setting, indirect reference to a concrete loc

    loc_ref: Optional[Identifier] = Field(None, init_var=True)  # sugar for criteria={'alias': ref}
    req_criteria: StringMap = Field(default_factory=dict, alias="loc_criteria")
    req_predicate: Predicate = Field(None, alias="loc_predicate")

    @property
    def location(self) -> Location | None:
        return self.provider

    @location.setter
    def dest(self, value: Location | None) -> None:
        self.provider = value

    @field_validator('label', mode="after")
    @classmethod
    def _uniquify_label(cls, data):
        if data and not data.startswith("se-"):
            return f"se-{data}"
        return data

    # locs may come with assets that should be inherited by the assigned place
    # assets: list[Asset] = None  # assets associated with the place

    def scout(self, location: Location = None) -> Location:
        """
        Assign, find, or create or find a suitable place for this location.

        If successful, it also associates the place with the location.

        If no place can be found, it returns None.
        If a place is created or discovered but cannot be associated, it raises an association error.
        """
        if location is None:
            self._resolve_successor()
            if location is not None:
                self.associate_with(location)
        return self.location

    def unscout(self):
        if self.location is None:
            return self.disassociate_from(self.location)

    # @on_can_associate.register()
    def _already_scouted(self, **kwargs):
        if self.location is not None:
            logger.warning(f"Already scouted place for {self!r}, must unscout before rescouting")
        return True

