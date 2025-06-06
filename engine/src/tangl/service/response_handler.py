from typing import Literal
import logging

from markdown_it import MarkdownIt

from tangl.mechanics.demographics import DemographicSampler

logging.getLogger('markdown_it').setLevel(logging.WARNING)

from tangl.type_hints import StringMap
from tangl.core.handler import HandlerRegistry
# from tangl.utils.response_models import BaseResponse

OutputMode = Literal["html", "ascii"]

on_handle_response = HandlerRegistry(default_aggregation_strategy="pipeline")

class ResponseHandler:

    @on_handle_response.register()
    @staticmethod
    def md_text_items(response: 'BaseResponse', **kwargs):
        md = MarkdownIt()
        if hasattr(response, "text") and isinstance(response.text, str) and response.text:
            response.text = md.render(response.text)
        return response, kwargs

    @classmethod
    def handle_response(cls,
                        response: list['BaseResponse'] | 'BaseResponse',
                        **kwargs) -> 'BaseResponse':
        if isinstance(response, list):
            for item in response:
                cls.handle_response(item, **kwargs)
        else:
            return on_handle_response.execute(response, **kwargs)
