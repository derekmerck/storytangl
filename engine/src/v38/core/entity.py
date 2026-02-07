# tangl/core/entity.py
from __future__ import annotations
from typing import Self

from .bases import HasIdentity, Unstructurable


class Entity(Unstructurable, HasIdentity):
    """
    Base for all managed objects.

    - Entities have identity and have round-trip un/structurable
    - mro order causes entities to compare by _value_ by default

    Example:
        >>> e = Entity(label='abc')
        >>> f = Entity(uid=e.uid, label=e.label)
        >>> e is not f and e.eq_by_value(f) and e == f
        True
    """

    def __init__(self, ctx = None, **kwargs) -> None:
        super().__init__(**kwargs)
        if ctx is not None:
            # chance to validate before finalizing
            from .dispatch import do_init
            do_init(caller=self, ctx=ctx)

    @classmethod
    def structure(cls, data, ctx = None) -> Self:
        if ctx is not None:
            # chance to modify kind-hint or construction kwargs
            from .dispatch import do_create
            data = do_create(data=data, ctx=ctx)
        return super().structure(data)
