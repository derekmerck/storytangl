import logging
from typing import Optional
import logging

from pydantic import model_validator, BaseModel, Field

from tangl.type_hints import UniqueLabel
from .singleton import Singleton

logger = logging.getLogger(__name__)


class InheritingSingleton(Singleton):
    """
    A Singleton mixin that supports attribute inheritance from existing instances.

    Attributes are inherited from a reference instance and can be selectively overridden.
    This creates an inheritance chain without requiring class inheritance.  The inheritance
    is controlled by the 'from_ref' keyword argument.

    Be careful to load them in order, the code does not provide any dependency resolution,
    and inheritance is not tracked.

    Example:
        base = MySingleton(label="base", value=1, other=2)
        child = MySingleton(label="child", from_ref="base", value=3)
        # child.value == 3, child.other == 2

    Parameters:
        from_ref (str): The label of the reference entity to inherit attributes from.
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
                exclude_unset=True, exclude_defaults=True, exclude_none=True,
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
