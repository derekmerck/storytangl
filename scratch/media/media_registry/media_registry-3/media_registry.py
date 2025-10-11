from __future__ import annotations
from uuid import UUID
from pathlib import Path
from typing import Callable, ClassVar, Type
import logging
from collections import Counter

from pydantic import BaseModel, Field

from tangl.type_hints import UniqueLabel, Pathlike, Tags
from tangl.core.registry import RegistryHandler
from tangl.core.singleton import RegistrySingleton
from .media_record import MediaRecord

logger = logging.getLogger(__name__)

class MediaRegistryHandler(RegistryHandler):

    record_cls: ClassVar[Type[MediaRecord]] = MediaRecord

    @classmethod
    def find_records(cls,
                     registry: MediaRegistry,
                     identifier: UniqueLabel | UUID = None,
                     tags: Tags = None) -> list[MediaRecord]:

        return MediaRecord._filter_instances(registry.values(),
                                             identifier = identifier,
                                             tags = tags)

        # res = []
        # for item in registry.data.values():
        #     if identifier and item.has_alias(identifier):
        #         res.append(item)
        #     elif tags and item.has_tags(*tags):
        #         res.append(item)
        # return res

    @classmethod
    def find_record(cls, registry: MediaRegistry,
                    identifier: UniqueLabel | UUID = None,
                    tags: Tags = None) -> MediaRecord:
        res = cls.find_records(registry, identifier=identifier, tags=tags)
        if res:
            return res[0]

    @classmethod
    def add_record(cls, registry: MediaRegistry, record: MediaRecord):
        registry.data[record.uid] = record

    @classmethod
    def create_record(cls,
                      registry: MediaRegistry,
                      label: UniqueLabel,
                      **kwargs) -> MediaRecord:
        record = cls.record_cls(label=label, **kwargs)
        if hasattr(record, 'path'):
            logger.debug(f"Registered file record with path: {record.path}")
        cls.add_record(registry, record)
        return record

    # @classmethod
    # def get_all_tags(cls, registry: MediaRegistry) -> Counter:
    #     res = Counter()
    #     for item in registry.data.values():
    #         res.update(item.tags)
    #     return res

class MediaRegistry(RegistrySingleton[UUID, MediaRecord]):
    """
    Like the strategy registry class, media registries are separated by instance domains for each "world"

    A MediaRegistry manages a set of resource collections (sub-domains) for a World and its
    associated stories.  Each resource location manages the various data objects under its
    purview.

    A registry can be accessed via its World, or via the ResourceHandler class via its domain name.
    """

    # data: dict[UUID, MediaRecord] = Field(default_factory=dict, init=False)

    def find_records(self,
                     identifier: UniqueLabel | bytes = None,
                     tags: Tags = None) -> list[MediaRecord]:
        return MediaRegistryHandler.find_records(self, identifier=identifier, tags=tags)

    def find_record(self,
                    identifier: UniqueLabel | bytes = None,
                    tags: Tags = None) -> MediaRecord:
        return MediaRegistryHandler.find_record(self, identifier=identifier, tags=tags)

    def add_record(self, record: MediaRecord):
        MediaRegistryHandler.add_record(self, record)

    def create_record(self, label: UniqueLabel, tags: Tags = None, **kwargs) -> MediaRecord:
        return MediaRegistryHandler.create_record(self, label=label, tags=tags, **kwargs)


class HasMediaRegistry(BaseModel):
    """
    Alternative way to access a resource registry directly on an Entity, without
    dereferencing the domain name via the resource handler.
    """
    media_registry: MediaRegistry = None

    def find_records(self, identifier: UniqueLabel = None, tags: Tags = None) -> list[MediaRecord]:
        return self.media_registry.find_records(identifier=identifier, tags=tags)

    def find_record(self, identifier: UniqueLabel, tags: Tags = None) -> MediaRecord:
        return self.media_registry.find_record(identifier=identifier, tags=tags)
