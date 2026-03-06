# tangl/core/singleton/inheriting_singleton.py
from typing import Optional
import logging

from pydantic import model_validator, BaseModel, Field

from tangl.type_hints import UniqueLabel
from .singleton import Singleton

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

class InheritingSingleton(Singleton):
    """
    InheritingSingleton(label: UniqueStr, from_ref: UniqueStr)

    Singleton that can inherit default attributes from another instance.

    Why
    ----
    Compose constant families (e.g., "Default Camera" → "Portrait Camera") without
    subclassing. Useful for fabula vocabularies, media presets, etc.

    Key Features
    ------------
    * **Reference instances** – Defaults copied from a reference instance of same class before validation.
    * **Selective override/merge** – dicts merged (``ref | data``), sets unioned, sequences extended.
    * **Order-sensitive** – no dependency resolution; parents must be created first.

    API
    ---
    - :attr:`from_ref` – label of the source instance; consumed during model validation.
    - Validator :meth:`_set_defaults_from_refs` – merges fields from the reference.

    Notes
    -----
    Inheritance is not tracked; add your own metadata if you need lineage auditing.
    """
    from_ref: Optional[UniqueLabel] = Field(None, init_var=True)
    """The label of the reference entity to inherit attributes from.
    Consumed by initialization."""

    # noinspection PyNestedDecorators
    @model_validator(mode="before")
    @classmethod
    def _set_defaults_from_refs(cls, data):
        if from_ref := data.pop('from_ref', None):
            logger.debug(f"Inheriting from {from_ref}")
            ref_instance = cls.get_instance(from_ref)

            if ref_instance is None:
                raise KeyError(
                    f"Cannot inherit from non-existent instance label: {from_ref} "
                    f"while creating <{cls.__name__}:{data.get('label', '<unknown>')}>"
                )
            defaults = BaseModel.model_dump(ref_instance,
                exclude_unset=True,
                exclude_defaults=True,
                exclude_none=True,
                exclude={"uid", "label", "from_ref"})
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
