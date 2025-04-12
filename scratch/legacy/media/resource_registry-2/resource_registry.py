from __future__ import annotations
from typing import Protocol, Callable

from pydantic import PrivateAttr, BaseModel

from tangl.entity import SingletonEntity
from tangl.type_hints import Pathlike
from .resource_location import ResourceLocation
from .resource_inventory_tag import ResourceInventoryTag as RIT

class ResourceRegistry(SingletonEntity):
    """
    A ResourceRegistry manages a set of resource locations for a World and associated stories.  Each resource location manages the various data objects under its purview.

    A registry can be accessed via its World, or via the ResourceHandler class via its domain name.
    """

    _locations: list[ResourceLocation] = PrivateAttr(default_factory=list)

    def add_file_location(self, base_path: Pathlike,
                          tagging_func: Callable = None,
                          extra_suffixes: list[str] = None):
        from .file_resource import FileResourceLocation
        loc = FileResourceLocation(base_path=base_path,
                                   tagging_func=tagging_func,
                                   extra_suffixes=extra_suffixes)
        self.add_location(loc)

    def add_location(self, loc: ResourceLocation):
        self._locations.append( loc )

    def find_resource(self, *aliases, **kwargs) -> RIT:
        for loc in self._locations:
            if x := loc.find_resource(*aliases, **kwargs):
                return x

    def find_resources(self, *aliases, **kwargs) -> list[RIT]:
        results = []
        for loc in self._locations:
            if x := loc.find_resources(*aliases, **kwargs):
                results.extend(x)
        if results:
            return results

    def update_inventory(self, **kwargs):
        for loc in self.locations:
            loc.update_inventory(**kwargs)


class HasResourceRegistry(BaseModel):
    """
    Alternative way to access a resource registry directly on an Entity, without
    dereferencing the domain name via the resource handler.
    """
    resource_registry: ResourceRegistry = None
