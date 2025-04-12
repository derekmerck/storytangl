from __future__ import annotations
from typing import Protocol, TYPE_CHECKING
from uuid import UUID

from tangl.graph import Node
from .type_hints import MediaResource
from tangl.resource_registry import ResourceInventoryTag as RIT


# Media creation

class MediaForgeProtocol(Protocol):

    @classmethod
    def get_instance(cls) -> MediaForgeProtocol:
        # forges are singleton entities
        ...

    def create_media(self, media_spec: MediaSpecProtocol, **kwargs) -> tuple[MediaResource, MediaSpecProtocol]:
        # returns the media and a possibly revised spec
        ...


class MediaSpecProtocol(Protocol):
    """
    MediaSpec classes are associated with different MediaForge types
    """
    uid: UUID

    def realize(self, node: Node = None, **overrides) -> MediaSpecProtocol: ...
    # Evolve a spec given reference node and override kwargs,
    # MediaSpec's aren't always associated with a single MediaRef

    @classmethod
    def get_forge(cls, **forge_kwargs) -> MediaForgeProtocol: ...


# Media Registry

class ResourceRegistryProtocol(Protocol):
    # a container for a collection of resource locations

    def add_resource(self, resource: MediaResource, **rit_kwargs) -> 'RIT':
        # pass any RIT kwarg, including data hashes and aliases
        ...

    def find_resource(self, *aliases, **kwargs) -> 'RIT':
        # returns inventory tag, which can be used at the service layer to
        # compute the actual server-relative url
        ...
