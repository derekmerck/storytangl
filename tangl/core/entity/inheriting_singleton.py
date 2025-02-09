from pydantic import model_validator, Field

from tangl.type_hints import UniqueLabel
from .singleton import Singleton


class InheritingSingleton(Singleton):

    from_ref: UniqueLabel = Field(None, alias='from')

    # noinspection PyNestedDecorators
    @model_validator(mode="before")
    @classmethod
    def _set_defaults_from_ref(cls, data):
        # todo: check for ref and get defaults for unset attribs
        return data
