from __future__ import annotations
from typing import Protocol, Callable

from pydantic import PrivateAttr, BaseModel

from tangl.entity import SingletonEntity
from tangl.type_hints import Pathlike
from .media_collection import MediaCollection
from .resource_inventory_tag import ResourceInventoryTag as RIT

class MediaRegistry(SingletonEntity):


    _collections: list[ResourceCollection] = PrivateAttr(default_factory=list)

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

