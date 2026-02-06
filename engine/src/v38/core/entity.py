# tangl/core/entity.py
from __future__ import annotations

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
    ...
