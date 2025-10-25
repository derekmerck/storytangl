from __future__ import annotations
from typing import Optional, Protocol, runtime_checkable, Any

# from media.old.protocols import MediaSpecP
from tangl.compilers.story_script import BaseScriptItem
from tangl.type_hints import Pathlike, Identifier, StringMap, Expr

# Interfaces for media-related deps, resources, and creators

Media = object
EntityP = Protocol
BaseScriptItemP = Protocol
DependencyEdgeP = Protocol
MediaRITP = Protocol

def media_handler(): ...

class DependencyEdgeP(BaseScriptItem):
    # discovery
    name: Optional[Identifier] = None
    criteria: Optional[StringMap] = None
    predicate: Optional[list[Expr]] = None
    # create
    template: Optional[StringMap] = None

class MediaDependencyP(BaseScriptItemP):
    # _name_, _criteria_, _predicate_           - Discover a RIT with these features
    template: Optional[MediaSpecP] = None       # Discover or create a RIT with this template
    path: Optional[Pathlike] = None             # Discover or create a RIT with this path
    data: Optional[Any] = None                  # Discover or create a RIT with this data
    # Has _one_ of path, data, template

    realized_template: Optional[MediaSpecP] = None   # Adapted for caller/parent node type
    final_template: Optional[MediaSpecP] = None      # Returned by prepare media

    # alias dest
    def rit(self) -> RIT: ...

    @media_handler()
    def prepare_media(self, ctx) -> tuple[MediaSpecP, Media]:
        self.realized_template = self.template.realize_for(ref=self.src)
        forge = self.realized_template.get_forge()
        self.final_template, media = forge.create_media(spec=self.realized_template)
        rit = MediaRITP(data=media, akas={self.realized_template.content_hash, self.final_template.content_hash})
        some_media_registry.add(rit)  # discoverable
        self.dest = some_media_registry, rit.uid

class MediaSpecP():
    creation_kwargs: StringMap

    @classmethod
    def get_forge(cls) -> MediaForgeP: ...

    def realize_for(self, ref: EntityP): ...  # generate a concrete spec for a reference


class MediaForgeP(Protocol):

    def create_media(self, spec: MediaSpecP) -> tuple[MediaSpecP, Media]:
        ...


class StableSpecP(MediaSpecP):
    aspect_ratio: float
    dims: tuple[int, ...]
    prompt: str
    n_prompt: str
    kwargs: {}

class VectorSpecP(MediaSpecP):
    aspect_ratio: float
    dims: tuple[int, ...]
    groups: list[str]
    styles: list[str] | dict[str, str] | None


