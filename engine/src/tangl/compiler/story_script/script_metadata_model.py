from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class UiConfig(BaseModel):
    brand_color: str = None  # html color value
    brand_font: str = None

class ScriptMetadata(BaseModel):
    title: str               # req
    author: str | list[str]  # req

    date: Optional[str | datetime] = None
    version: Optional[str] = None
    illustrator: Optional[str] = None
    license: Optional[str] = None
    summary: Optional[str] = None
    url: Optional[str] = None
    publisher: Optional[str] = None
    comments: Optional[str] = None

    # media: Optional[list[MediaItemScript]] = None
    ui_config: Optional[UiConfig] = None

    # @model_validator(mode='before')
    # @classmethod
    # def alias_text_to_comments(cls, values):
    #     _value = values.get('comments') or values.get('text')
    #     if _value is not None:
    #         values['comments'] = _value
    #     return values
