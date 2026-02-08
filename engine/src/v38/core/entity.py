# tangl/core/entity.py
from __future__ import annotations
from typing import Self

from .bases import HasIdentity, Unstructurable


class Entity(Unstructurable, HasIdentity):
    """
    Base for all managed objects.

    Entities have identity and round-trip un/structurable serialization.
    By default, entities compare by value (via Unstructurable mixin).

    **Dispatch Hooks:**

    Pass `_ctx` to `__init__()` to trigger dispatch hooks (see core.dispatch):

        entity = Entity(label="foo", _ctx=runtime_ctx)
        # Triggers do_init() with registered behaviors

    The underscore prefix indicates _ctx is a control signal, not stored data.
    If a subclass has a `ctx` field for data storage, both can coexist:

        CallReceipt(result=5, ctx=context, _ctx=context)
        # ctx stored as field, _ctx triggers hooks

    Example:
        >>> e = Entity(label='abc')
        >>> f = Entity(uid=e.uid, label=e.label)
        >>> e is not f and e.eq_by_value(f) and e == f
        True
    """

    def __init__(self, _ctx = None, **kwargs) -> None:
        super().__init__(**kwargs)
        from .ctx import resolve_ctx
        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            from .dispatch import do_init
            do_init(caller=self, ctx=_ctx)

    @classmethod
    def structure(cls, data, _ctx = None) -> Self:
        from .ctx import resolve_ctx
        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            # chance to modify kind-hint or construction kwargs
            from .dispatch import do_create
            data = do_create(data=data, ctx=_ctx)
        return super().structure(data)
