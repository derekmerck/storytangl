from pydantic import BaseModel

from .base_response_model import BaseResponse

class StyleHints(BaseResponse):
    """
    Style hints need not be respected by the client, although style_dict['color'] is
    usually easy to implement.

    Attributes:
    - style_dict (dict[str, str]): Suggested HTML style attributes
    - style_cls (list[str]): Suggested HTML .classes for styling
    - style_id (str): Suggested HTML #id
    """
    style_dict: dict[str, str] = None
    style_cls: list[str] = None
    style_id: str = None
