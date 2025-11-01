import logging

from pydantic import Field, model_validator

from tangl.type_hints import StringMap, Identifier
from tangl.core import Graph
from tangl.vm.provision import Dependency
from tangl.vm import ProvisioningPolicy
from .location import Location

logger = logging.getLogger(__name__)

class Setting(Dependency[Location]):
    # Scene setting, indirect reference to a concrete loc

    @property
    def location(self) -> Location | None:
        return self.requirement.provider

    @location.setter
    def location(self, value: Location) -> None:
        self.requirement.provider = value

    # init helpers
    location_ref: Identifier = Field(None, init_var=True)
    location_criteria: StringMap = Field(None, init_var=True)
    location_template: StringMap = Field(None, init_var=True)
    requirement_policy: ProvisioningPolicy = Field(None, init_var=True)

    @model_validator(mode="before")
    @classmethod
    def _validate_req(cls, data):
        if 'requirement' not in data:
            req = {
                'identifier': data.pop('location_ref', None),
                'criteria': data.pop('location_criteria', {}),
                'template': data.pop('location_template', None),
                'policy': data.pop('requirement_policy', ProvisioningPolicy.ANY),
                'graph': data['graph']
            }
            if req['template'] is not None:
                # we can infer the object cls of the template
                req['template'].setdefault('obj_cls', Location)
            if req['criteria'] is not None:
                req['criteria'].setdefault('is_instance', Location)
            data['requirement'] = req
        return data

    # @field_validator('label', mode="after")
    # @classmethod
    # def _uniquify_label(cls, data):
    #     if data and not data.startswith("se-"):
    #         return f"se-{data}"
    #     return data
    #
    # # locs may come with assets that should be inherited by the assigned place
    # # assets: list[Asset] = None  # assets associated with the place
    #
    # def scout(self, location: Location = None) -> Location:
    #     """
    #     Assign, find, or create or find a suitable place for this location.
    #
    #     If successful, it also associates the place with the location.
    #
    #     If no place can be found, it returns None.
    #     If a place is created or discovered but cannot be associated, it raises an association error.
    #     """
    #     if location is None:
    #         self._resolve_successor()
    #         if location is not None:
    #             self.associate_with(location)
    #     return self.location
    #
    # def unscout(self):
    #     if self.location is None:
    #         return self.disassociate_from(self.location)
    #
    # # @on_can_associate.register()
    # def _already_scouted(self, **kwargs):
    #     if self.location is not None:
    #         logger.warning(f"Already scouted place for {self!r}, must unscout before rescouting")
    #     return True

