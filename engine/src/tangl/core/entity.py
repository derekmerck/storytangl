# tangl/core/entity.py
from __future__ import annotations

import logging
from typing import Any, Self

from pydantic import Field

from tangl.type_hints import Hash

from .bases import HasIdentity, Unstructurable, is_identifier
from .namespace import HasNamespace

match_logger = logging.getLogger(__name__ + ".match")


class Entity(Unstructurable, HasIdentity, HasNamespace):
    """Canonical concrete core entity composed from identity + constructor-form traits.

    Why
    ---
    :class:`Entity` is intentionally minimal. It adds no persistent fields beyond
    :class:`Unstructurable` and :class:`HasIdentity` and exists mainly to:

    - fix the default trait composition order for core entities, and
    - inject lifecycle dispatch hooks during creation paths.

    Notes
    -----
    Inheritance order is ``(Unstructurable, HasNamespace, HasIdentity)``.
    ``HasNamespace`` adds namespace contribution behavior, while ``__eq__`` still
    compares by value via :meth:`Unstructurable.eq_by_value`.

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
    :mod:`tangl.core.dispatch`
        Hook registration and execution behavior.
    :mod:`tangl.core.ctx`
        Ambient context helpers for hook propagation.
    """

    templ_hash: Hash | None = Field(default=None, json_schema_extra={"is_identifier": True})
    """Optional provenance hash of the template used to materialize this entity."""

    def is_instance(self, kind: type | tuple[type, ...]) -> bool:
        """Legacy alias for ``has_kind``."""
        if isinstance(kind, tuple):
            return all(isinstance(c, type) for c in kind) and isinstance(self, kind)
        return isinstance(kind, type) and isinstance(self, kind)

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
