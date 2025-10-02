from typing import Literal
import logging

from markdown_it import MarkdownIt

logging.getLogger('markdown_it').setLevel(logging.WARNING)

from tangl.core.dispatch import DispatchRegistry
from .content_response import ContentResponse

OutputMode = Literal["html", "ascii"]

on_handle_response = DispatchRegistry(aggregation_strategy="pipeline")

class ResponseHandler:

    @on_handle_response.register()
    @staticmethod
    def md_text_items(caller: ContentResponse, **kwargs):
        response = caller
        md = MarkdownIt()
        if hasattr(response, "text") and isinstance(response.text, str) and response.text:
            response.text = md.render(response.text)
        return response, kwargs

    @classmethod
    def handle_response(cls,
                        response: ContentResponse,
                        **kwargs) -> ContentResponse:
        if isinstance(response, list):
            for item in response:
                cls.handle_response(item, **kwargs)
        else:
            return on_handle_response.execute_all_for(response, **kwargs)
