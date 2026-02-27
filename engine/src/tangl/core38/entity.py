# tangl/core/entity.py
from __future__ import annotations

from typing import Any, Self

from .bases import HasIdentity, Unstructurable


class Entity(Unstructurable, HasIdentity):
    """Canonical concrete core entity composed from identity + constructor-form traits.

    Why
    ---
    :class:`Entity` is intentionally minimal. It adds no persistent fields beyond
    :class:`Unstructurable` and :class:`HasIdentity` and exists mainly to:

    - fix the default trait composition order for core entities, and
    - inject lifecycle dispatch hooks during creation paths.

    Notes
    -----
    Inheritance order is ``(Unstructurable, HasIdentity)``, so ``__eq__`` compares
    by value via :meth:`Unstructurable.eq_by_value`.

    - Two entities with the same ``uid`` but different constructor-form values are
      not equal under ``==``.
    - Use :meth:`HasIdentity.eq_by_id` when you need identity-only comparison.

    **Dispatch hook control signal**

    Pass ``_ctx`` to ``__init__`` or :meth:`structure` to activate dispatch hooks.
    The underscore prefix means this is a control argument and is not stored as model
    data. If a subclass also has a ``ctx`` data field, both can coexist:

    .. code-block:: python

        CallReceipt(result=5, ctx=context, _ctx=context)

    Example:
        >>> e = Entity(label="abc")
        >>> f = Entity(uid=e.uid, label=e.label)
        >>> e is not f and e.eq_by_value(f) and e == f
        True
        >>> e.eq_by_id(f)
        True
        >>> g = Entity(uid=e.uid, label="different")
        >>> e.eq_by_id(g) and e != g
        True

    See Also
    --------
    :mod:`tangl.core38.dispatch`
        Hook registration and execution behavior.
    :mod:`tangl.core38.ctx`
        Ambient context helpers for hook propagation.
    """

    templ_hash: str | None = None
    """Optional provenance hash of the template used to materialize this entity."""

    def __init__(self, _ctx: Any = None, **kwargs: Any) -> None:
        """Construct the entity and optionally run ``on_init`` dispatch hooks."""
        super().__init__(**kwargs)
        from .ctx import resolve_ctx

        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            from .dispatch import do_init

            do_init(caller=self, ctx=_ctx)

    @classmethod
    def structure(cls, data: Any, _ctx: Any = None) -> Self:
        """Structure from constructor-form data and optionally run ``on_create`` hooks."""
        from .ctx import resolve_ctx

        _ctx = resolve_ctx(_ctx)
        if _ctx is not None:
            # chance to modify kind-hint or construction kwargs
            from .dispatch import do_create

            data = do_create(data=data, ctx=_ctx)
        return super().structure(data)
