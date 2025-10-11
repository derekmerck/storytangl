from __future__ import annotations
from typing import Protocol, Type, Any, ClassVar, Iterable
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field

from tangl.type_hints import UniqueLabel, String, Tag, StringMap
from tangl.core import ResourceInventoryTag
from tangl.media import MediaRole



class MediaSpec(StoryLink):

    media_role: MediaRole = None

    @property
    def media_record(self) -> MediaRecord:
        return self.successor

    successor_ref: UniqueLabel | UUID = Field(None, alias='media_ref', description="name, path, existing template hash, or data hash")
    successor_template: StringMap = Field(None, alias='media_template', description="create media on-demand using a template")

    # find satisfying media
    successor_conditions: Strings = Field(None, alias='media_conditions', description="Use existing media meeting conditions")
    successor_tags: Tags = Field(None, alias='media_tags', description="Use existing media with these tags")

    successor_cls: ClassVar = MediaRecord
    successor_parent: ClassVar = False

    @property
    def label(self):
        # Uniquify the label in case the media is named with its own ref
        super_label = super().label
        if super_label and not super_label.startswith("mx-"):
            return f"mx-{super_label}"
        return super_label

    @property
    def template_hash(self) -> bytes:
        if self.media_template:
            return hash_for_secret(str(self.media_template.creation_kwargs))


class MediaCreationHandler(BaseHandler):
    """
    Analogous to the casting or scouting handler's 'create' mechanism except
    the media template has to be preprocessed and "realized" with respect to
    the spec-holder.

    That is, the invoking story node is passed along with the template to create
    a "real" specification for the media.  This is handled similarly to how the
    RenderHandler creates a composite dict of jinja-rendered items.
    """

    @BaseHandler.strategy("on_realize_media_config", priority=Priority.EARLY)
    @staticmethod
    def _include_template_kwargs(media_template: BaseModel, result_node: StoryNode = None, **kwargs) -> dict[str, Any]:
        return media_template.model_dump()

    @classmethod
    def realize_media_config(cls,
                             media_template: MediaTemplate,
                             reference_node: StoryNode,
                             **kwargs) -> StringMap:
        return cls.execute_task(media_template, "on_realize_media_config", reference_node=reference_node, result_mode="merge", **kwargs )

    @classmethod
    def create_media(cls, media_template: MediaTemplate, reference_node: StoryNode) -> tuple[Media, dict]:
        kwargs = cls.realize_media_config(media_template, reference_node)
        media = media_template.media_creation_handler.create_media(**kwargs)
        return media, kwargs


class MediaTemplate(BaseModel):
    media_creation_handler: ClassVar[Type[MediaCreationHandler]]
    media_config: StringMap


class HasMedia(BaseModel):
    # Similar to roles for a scene, can reference by index or label/name

    @property
    def media(self) -> Iterable[MediaSpec]:
        return self.find_children(MediaSpec)

    def media_map(self) -> dict[MediaRole | str, MediaRecord]:
        return {
            m.media_role: m.media_record for m in self.media if m.media_record is not None
        } | {
            m.label: m.media_record for m in self.media if m.media_record is not None
        }
