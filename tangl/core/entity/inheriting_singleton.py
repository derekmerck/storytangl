from copy import copy

from pydantic import model_validator, Field, BaseModel

from tangl.type_hints import UniqueLabel
from .singleton import Singleton


class InheritingSingleton(Singleton):

    from_ref: UniqueLabel = None

    # noinspection PyNestedDecorators
    @model_validator(mode="before")
    @classmethod
    def _set_defaults_from_refs(cls, data):
        if from_ref := data.get('from_ref'):
            ref_instance = cls._instances[from_ref]
            defaults = BaseModel.model_dump(
                ref_instance, exclude_unset=True, exclude_defaults=True, exclude_none=True)
            for k, v in defaults.items():
                if k in data:
                    # include items from reference class in collections
                    if isinstance(data[k], set):
                        data[k] = data[k].union(v)
                    elif isinstance(data[k], dict):
                        data[k] = v | data[k]
                    elif isinstance(data[k], (list, tuple)):
                        data[k].extend(v)
                else:
                    data.setdefault(k, v)
        return data
