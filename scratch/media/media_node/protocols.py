from __future__ import annotations
from typing import Protocol, Self, Optional
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from tangl.core import TaskPipeline, PipelineStrategy
from tangl.type_hints import UniqueLabel, StringMap
from tangl.core import Singleton, Registry
from tangl.core.graph import Node
from tangl.media.type_hints import Media

# Media Node


class MediaEdge(Node):

    media_ref: UniqueLabel = None  # node label/path in the graph
    media_template: StringMap = None
    media_criteria: StringMap = None

    media_record_id: Optional[UUID] = None

    def resolve_media(self, **context: Any) -> Media:
        return on_resolve_media.execute(self, **context)

    def get_media_record(self, **context: Any) -> MediaRecordP:
        if self.media_record_id is None:
            self.resolve_media(**context)
        return MediaRecordRegistryP.get(self.media_record_id)


# Media creation

class MediaForgeABC(Singleton):
    """
    Singleton
    """

    @classmethod
    def get_forge_for(cls: Self, spec: MediaSpecP) -> Self:
        return cls._instances.find_one(spec=spec)

    def has_spec(self, spec: MediaSpecP) -> bool:
        """
        Returns true if the forge can handle this spec.
        `has_spec` naming enables search with `find(spec=x)` syntax.
        """
        ...

    def create_media(self, media_spec: MediaSpecP, **kwargs) -> tuple[Media, MediaSpecP]:
        """Returns the media object and a potentially revised spec"""
        ...


class MediaSpecP(Protocol):
    """
    MediaSpec classes are associated with different MediaForge types
    """
    def realize(self, referent: Node = None, **overrides) -> MediaSpecP:
        """
        Evolve a spec given a referent Node and override kwargs.
        MediaSpec's can be associated with multiple MediaNodes, each of which
        will generate a different Media resource (and media record).
        """
        ...

# Media Registry

class MediaRecordP(Protocol):
    """
    Inventory tag that maps from MediaNode/MediaSpec aliases to Media resources,
    usable by the service layer to compute an actual server-relative media url.
    """

    def get_media_resource(self):
        ...

class MediaRecordRegistryP(Registry[MediaRecordP]):
    """Searchable index of media records"""

    def add_record(self, source: MediaNode | MediaSpecP, media: Media) -> MediaRecordP:
        # Create a new rit, including data hashes and aliases
        ...

    def update_record(self, source: Optional[MediaNode | MediaSpecP], media: Optional[Media]) -> MediaRecordP:
        # Create a new rit, including data hashes and aliases
        ...




class MediaForge(ABC, Singleton):

    @abstractmethod
    def create_media(self, spec: MediaSpec) -> tuple[Media, MediaSpec]:
        ...


class MediaSpec(ABC, Entity):

    @abstractmethod
    def get_forge(self) -> MediaForge:
        ...

# todo: forges should just register whether they can handle certain types with a dispatcher
#       they can use "first" to nominate themselves to handle a spec, like an object class being processed.


class RasterImageSpec(MediaSpec):

    dims: tuple[int, int]
    composites: list[str]


class VectorImageSpec(MediaSpec):

    shapes: list[str]
    palette: Any
    scale: dict


# class SourceManager(ABC, SingletonEntity):
#
#     def get_source_items(self, *items) -> Any:
#         ...
#
# class TransformedImage(Image.Image):
#
#     def __init__(self,
#                  *args,
#                  position: tuple[int, int] = (0, 0),
#                  **kwargs):
#         self.position = position
#         super().__init__(*args, **kwargs)
#
#
# class ImageAssember(ABC):
#
#     @abstractmethod
#     def assemble_image(self, *args, **kwargs):
#         ...
#
#
# class RasterImageAssember(ImageAssember):
#
#     def assemble_image(self,
#                        layers: list[Image.Image],
#                        dims: tuple[int, int] = (512, 512)):
#
#         im = Image.new("RGBA", dims)
#
#         for shape in shapes:
#             ...
#
#
#
#
# class ImageForge(MediaForge):
#
#     source_manager: ClassVar[SourceManager]    # svg im or raster source dir
#     image_assembler: ClassVar[ImageAssembler]  # svg or raster
#
#     def create_media(self, spec: ImageSpec) -> tuple[Media, MediaSpec]:
#         shapes = self.source_manager.get_source_items(spec.shapes)
#         # update shapes if random selections were made
#         media = self.image_assembler.assemble(
#             shapes=shapes,
#             palette=spec.palette,
#             scale=spec.scale
#         )
#         return media, spec
#

