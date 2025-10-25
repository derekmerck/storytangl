from __future__ import annotations
from uuid import UUID
from pydantic import Field, field_validator

from tangl.type_hints import Identifier, StringMap, Tag
from tangl.core import HasContext, ResourceInventoryTag, DynamicEdge, HandlerPipeline, PipelineStrategy, HandlerPriority, ResourceRegistry, Node
from .media_spec import MediaSpec

on_resolve_media = HandlerPipeline[Node, ResourceInventoryTag](
    label="resolve_media",
    pipeline_strategy=PipelineStrategy.FIRST)

on_resolve_spec = HandlerPipeline[Node, MediaSpec](
    label="resolve_spec",
    pipeline_strategy=PipelineStrategy.FIRST)

class MediaNode(HasContext, DynamicEdge[ResourceInventoryTag]):
    """
    Similar to a Role->Actor or Setting->Location edge, a MediaNode is a placeholder
    for a media resource that may not exist yet.

    Instead of referencing the media directly though, it holds a key for a media record,
    which can be further dereferenced by the response handler at the service layer.

    MediaNodes may be assigned in several ways:
    - By referring to an existing RIT using `media_ref`
    - By searching for a RIT in a registry that matches `actor_criteria`
    - By specifying a MediaSpec to use to create new or discovery existing media.
      MediaSpec's can be defined inline with `media_spec`, or given as a `media_spec_ref`
      or `media_spec_criteria`, just like other indirect links.

    :ivar media_ref: The identifier of an existing media RIT to fill this node
    :ivar media_criteria: Conditions for finding a media RIT to be assigned to this node
    :ivar media_spec: The specification for creating a media object and RIT to fill this node
    :ivar media_spec_ref: The identifier for finding a spec to create a media object and RIT
    :ivar media_spec_criteria: Conditions for finding a spec to create a media object and RIT

    MediaNode will raise an error if it cannot be dereferenced.
    """

    successor_ref: Identifier = Field(None, alias="media_ref")
    successor_criteria: StringMap = Field(None, alias="media_criteria")

    successor_template_id: UUID = Field(None, alias="media_template_id")

    successor_template: StringMap = Field(None, alias="media_spec")
    successor_template_ref: Identifier = Field(None, alias="media_spec_ref")
    successor_template_criteria: StringMap = Field(None, alias="media_spec_criteria")

    @on_resolve_media.register(priority=HandlerPriority.EARLY)
    def _try_to_find_rit(self, **context):
        # If we can find a rit, we are done
        if self.successor_ref:
            if x := self.graph.find_one(alias=self.successor_ref, search_everywhere=True):
                return x
        elif self.successor_criteria:
            if x := self.graph.find_one(**self.successor_criteria, search_everywhere=True):
                return x

    # a lot of space between to intercept and alter the pipeline
    @on_resolve_media.register(priority=HandlerPriority.LATE)
    def _create_from_spec(self, **context):
        if not self.media_spec:
            return
        # create it
        revised_spec, media = self.media_spec.create_media(self, **context)
        # register it
        rit = ResourceInventoryTag.from_data(
            label=self.label,
            aliases=[revised_spec.uid, self.label],  # etc.
            data=media)
        return rit

    @on_resolve_spec.register(priority=HandlerPriority.EARLY)
    def _try_to_find_spec(self, **context):
        # Try to find a spec
        if self.successor_templte_ref:
            if x := self.graph.find_one(alias=self.successor_template_ref, search_everywhere=True):
                return x
        elif self.successor_criteria:
            if x := self.graph.find_one(**self.successor_template_criteria, search_everywhere=True):
                return x

    @on_resolve_spec.register(priority=HandlerPriority.LATE)
    def _create_a_new_spec(self, **context):
        if not self.successor_template:
            return
        # todo: set default type properly
        media_spec = Node.structure(self.successor_template)
        return media_spec

    def resolve_spec(self, **context):
        context = context or self.gather_context()
        return on_resolve_spec.execute(self, **context)

    def resolve_media(self, **context):
        context = context or self.gather_context()
        return on_resolve_media.execute(self, **context)

    @property
    def media(self) -> ResourceInventoryTag:
        return self.successor

    @field_validator('label', mode="after")
    @classmethod
    def _uniquify_label(cls, data):
        if data and not data.startswith("me-"):
            return f"me-{data}"
        return data
