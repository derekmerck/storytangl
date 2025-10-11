from __future__ import annotations
from typing import Protocol, Type, Self
from pathlib import Path
import hashlib
import abc

from pydantic import BaseModel, model_validator, AnyUrl, PrivateAttr, Field

from tangl.type_hints import UniqueLabel, Uid
from tangl.core.entity.fragment import BaseJournalItem
from tangl.core import on_render
from tangl.core.graph import Node  # BaseModel with parent/children
from tangl.media.type_hints import MediaResource
from tangl.script.script_models import BaseScriptItem
from tangl.utils.response_models import BaseResponse as BaseResponseItem, StyleHints
from tangl.story.actor import Actor


# ---------------------------
# Type Hints
# ---------------------------

class MediaForge(Protocol):
    @classmethod
    def create_media(cls, spec: BaseMediaSpec) -> tuple[MediaResource, BaseMediaSpec]: ...

class MediaForgeAdapter(Protocol):
    @classmethod
    def spec_from_ref(cls, ref: Node, spec_cls: Type[MediaSpec] = None, **kwargs) -> BaseMediaSpec: ...

class MediaRecord: ...
#
# class ResourceInventoryManager(Protocol):
#     @classmethod
#     def find(cls, *aliases: str) -> MediaRecord: ...
#     @classmethod
#     def register(cls, resource: MediaResource, *aliases: str) -> RIT: ...  # saves media as file in proper collection
#     @classmethod
#     def register_file(cls, fn: Path, *aliases: str) -> RIT: ...    # index files on disk -> RITs
#     @classmethod
#     def get_resource(cls, rit: RIT) -> MediaResource: ...
#     @classmethod
#     def get_resource_file(cls, rit: RIT) -> Path: ...

class MediaServer(Protocol):

    def get_base_url(self) -> AnyUrl: ...
    def get_media_collection_path(self, item: MediaRecord) -> Path: ...

# -----------------
# Media Script Item (input)
# -----------------

class MediaScriptItem(BaseScriptItem):
    url: AnyUrl = None
    data: bytes | str = None
    name: str = None
    spec: StableSpec | VectorSpec = None
    # stable spec must have a prompt, so this should discriminate

    @model_validator(mode='after')
    def _check_exactly_one_field(self):
        """
        Ensures that exactly one of `url`, `data`, `name`, or `spec` is provided.
        """
        fields = ['url', 'data', 'name', 'spec']
        provided_fields = sum(1 for field in fields if getattr(self, field) is not None)
        if provided_fields != 1:
            raise ValueError("Exactly one of 'url', 'data', 'name', or 'spec' must be provided.")
        return self


class MediaSpec(abc.ABC, BaseModel, extra="allow"):

    ref_id: UniqueLabel | Uid = None             # reference a specific node (role, actor, scene)

    @property
    def ref(self) -> Node:
        return self.story.get_node(self.node_ref)

    @abc.abstractmethod
    def realize(self, ref = None, **kwargs) -> Type[Self]: ...        # finalize and generate a concrete spec

    @classmethod
    @abc.abstractmethod
    def get_forge(cls) -> Type[MediaForge]: ...  # get an appropriate forge cls for processing this type of spec

    def get_thumbprint(self) -> str:
        return hashlib.sha3_224( self.model_dump() ).hexdigest()

# -----------------
# Media Node (live)
# -----------------

class MediaNode(MediaScriptItem, Node):
    script_spec: BaseMediaSpec = None    # as in script
    realized_spec: BaseMediaSpec = None  # relative to kwargs and ref
    final_spec: BaseMediaSpec = None     # returned by forge

    media_record: MediaRecord = None   # prepared media tag

    @model_validator(mode='after')
    def _check_ready(self):
        self.ready()

    def ready(self) -> bool:
        if self.url or self.data or self._rit:
            return True
        if rit := ResourceInventoryManager.find_tag(self.name, *self.get_thumbprints()):
            # look for item by name or any spec thumbprint
            self._rit = rit
            return True
        if self.spec and self.prepare_media():
            # try to create and register it
            return True
        return False

    def prepare_media(self) -> bool:
        # execute the spec on its forge with self.parent as ref
        if self._rit:
            return True
        forge = self.spec.get_forge()
        self.realized_spec = self.spec.realize(ref=self.parent)
        media, self.final_spec = forge.create_media(self.realized_spec)
        self._rit = ResourceInventoryManager.register(media, *self.get_media_aliases())
        return True

    def get_thumbprints(self):
        return [ spec.get_thumbprint() for spec in [ self.spec, self.realized_spec, self.final_spec ] if spec ]

    def render(self) -> dict:  # JournalMediaItem
        if not self.ready():
            raise RuntimeError("Unable to prepare data for jmi output")
        res = { 'url': self.url,
                'data': self.data,
                '_rit': self._rit }
        res = { k: v for k, v in res.items() if v }
        return res

# -----------------
# Media Specification Types (input, live)
# -----------------

# Raster Generative AI

StableForge = MediaForge
StableForgeAdapter = MediaForgeAdapter

class StableSpec(BaseMediaSpec):

    # ref: Actor, Scene, Block, Challenge/Game

    prompt: str
    n_prompt: str = Field(alias="negative_prompt", default=None)

    model: str = Field(alias="sd_model_name", default=None)
    sampler: str = Field(alias="sampler_name", default=None)
    steps: int = None
    dims: tuple[int, int] = None
    seed: int = None
    cfg_scale: float = 4.5

    def realize(self, ref: Node = None, **kwargs) -> Type[Self]:
        ref = ref or self.ref
        if self.ref or kwargs:
            return StableForgeAdapter.spec_from_node(self, ref=ref, **kwargs)

    @classmethod
    def get_forge(cls):
        return StableForge

# Vector

SvgForge = MediaForge
SvgForgeAdapter = MediaForgeAdapter
SvgGroup = object

class VectorSpec(BaseMediaSpec, StyleHints):
    # [ templates ]
    # ref: Actor, Scene, Block, Challenge/Game

    collection: str = None    # pull a single layer from the svg source collection
    shapes: list[SvgGroup] = None

    def realize(self, ref: Node = None, **kwargs) -> Type[Self]:
        ref = ref or self.ref
        if self.collection:
            return SvgForgeAdapter.spec_from_collection(ref.world.svg_sources,
                                                        self.collection,
                                                        **kwargs)
        elif self.ref and isinstance(self.ref, Actor):
            return SvgForgeAdapter.spec_from_paperdoll(ref.world.svg_paperdoll_sources,
                                                       actor=ref,
                                                       **kwargs)

    @classmethod
    def get_forge(cls):
        return SvgForge

# -----------------
# Journal Media Item (output)
# -----------------

class JournalMediaItem(BaseJournalItem):
    url: str = None
    data: bytes = None
    _rit: RIT = PrivateAttr(None)  # Response handler will dereference this field to a url or data and discard it

    @model_validator(mode='after')
    def _check_exactly_one_field(self):
        """
        Ensures that exactly one of `url`, `data`, `_rit` is provided.
        """
        fields = ['url', 'data', '_rit']
        provided_fields = sum(1 for field in fields if getattr(self, field) is not None)
        if provided_fields != 1:
            raise ValueError("Exactly one of 'url', 'data', or '_rit' must be provided.")
        return self

class JournalResponseHandler:
    # Called by the API as it processes rendered journal objects for a call response

    @classmethod
    def process_journal_media(cls, jmi: JournalMediaItem, media_server: MediaServer):
        if jmi._rit:
            base_url = media_server.get_base_url()
            media_url = media_server.get_media_collection_path(jmi._rit)     # music, images, whatever
            file_loc = ResourceInventoryManager.get_resource_file(jmi._rit)  # file name within collection
            jmi.url = base_url / media_url / file_loc
            # ...or could convert to inline `jmi.data` by getting the raw media data and encoding it
            jmi._rit = None
        return jmi