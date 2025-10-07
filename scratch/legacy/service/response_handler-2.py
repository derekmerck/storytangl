import logging
from typing import ClassVar

from markdown_it import MarkdownIt
from pydantic import BaseModel

from tangl.media import JournalMediaItem, MediaNode
from tangl.resource_registry import ResourceHandler

logging.getLogger("markdown_it").setLevel(logging.WARNING)

# todo: invoke on_handle_service_response plugin

class ResponseHandler:

    @classmethod
    def noop(cls, entry: BaseModel):
        return entry

    md: ClassVar = MarkdownIt()

    @classmethod
    def recursive_markdown(cls, response: BaseModel | list[BaseModel]):
        """If any fields are marked as markdown, render them to html."""
        if isinstance(response, list):
            for x in response:
                cls.recursive_markdown(x)
        elif isinstance(response, BaseModel):
            for field_name, field_info in response.model_fields.items():
                schema_extra = field_info.json_schema_extra or {}
                use_markdown = schema_extra.get('markdown', False)
                # todo: handle inline markdown for short fields like titles
                if (x := getattr(response, field_name)) is not None:
                    if isinstance(x, str) and use_markdown:
                        setattr(response, field_name, cls.md.render(x))
                    elif isinstance(x, BaseModel) or (isinstance(x, list) and isinstance(x[0], BaseModel)):
                        cls.recursive_markdown(x)

    @classmethod
    def dereference_media(cls, response: list[BaseModel] | BaseModel):
        """Convert all media RITs to media resources"""
        if isinstance(response, list):
            for x in response:
                cls.dereference_media(x)
        elif isinstance(response, BaseModel):
            for field_name, field_info in response.model_fields.items():
                if (x := getattr(response, field_name)) is not None:
                    if isinstance(x, JournalMediaItem):
                        # todo: Need to pass in calling service manager, too...
                        setattr(response, field_name, x.get_media_resource())
                    elif isinstance(x, BaseModel) or (isinstance(x, list) and isinstance(x[0], BaseModel)):
                        cls.dereference_media(x)

    # todo: as commented in MediaNode, we need to identify collections as belonging
    #       to the public media or client media domains so we can build the final
    #       location appropriately.

    # def get_media_resource_location(self, **kwargs) -> str:
    #     media_resource = self.get_media_resource(**kwargs)
    #     path_els = [self.registry.registry_domain,
    #                 self.registry.collection_id,
    #                 "media",
    #                 self.media_type,
    #                 media_resource.guid,
    #                 self.media_format.value]
    #     path = "/".join(path_els)
    #     return path

    # @field_validator('media')
    # @classmethod
    # def _convert_refs_to_resources(cls, values):
    #     # world media is generally going to be static, so we can do this late
    #     # in general, for stories, we want to do this much earlier
    #     return [ref.get_media_resource() for ref in values if isinstance(ref, MediaReference)]

    @classmethod
    def format_response(cls, response: list[BaseModel] | BaseModel):
        """
        - Apply markdown to text fields in Response objects or lists of Response objects
        - Dereference media RITs from JournalMediaItems or lists of JMI's
        - Call 'on_handle_service_response' plugin handler if available
        """
        cls.recursive_markdown(response)
        return response
