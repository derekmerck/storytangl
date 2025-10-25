from __future__ import annotations
from uuid import UUID
from typing import Iterable

from .enums import ResourceDataType
from .resource_inventory_tag import ResourceInventoryTag as RIT
from tangl.utils.alias_dict import HasAliases, AliasDict


class ResourceLocation(AliasDict[UUID | str, RIT]):
    # Collection of resources

    def update_inventory(self, **kwargs):
        pass

    def _save_resource_file(self, resource_tag: RIT, resource = None):
        raise NotImplementedError

    def add_resource(self, resource_tag: RIT, resource = None):
        if resource:
            self._save_resource_file(resource_tag, resource)
        self.add(resource_tag)

    def find_resources(self,
                       *aliases,
                       resource_type: ResourceDataType = None,
                       has_tags: set = None) -> list[RIT]:

        filts = []
        if resource_type:
            filts.append( lambda x: x.resource_type is resource_type )
        if has_tags:
            if not isinstance(has_tags, Iterable):
                has_tags = [has_tags]
            filts.append( lambda x: x.has_tags(*has_tags) )

        def combined_filter(x):
            return all(filt(x) for filt in filts)

        return self.find_items(*aliases, filt=combined_filter if filts else None)

    def find_resource(self,
                      *aliases,
                      resource_type: ResourceDataType = None,
                      has_tags: set = None) -> RIT:
        res = self.find_resources(*aliases, resource_type=resource_type, has_tags=has_tags)
        if res:
            return res[0]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_inventory()
