# tangl/core/entity.py
from __future__ import annotations

from typing import Any, Iterable, Iterator, Self
from enum import Enum
import re

from .bases import HasIdentity, Unstructurable
from .namespace import HasNamespace


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
    :mod:`tangl.core38.dispatch`
        Hook registration and execution behavior.
    :mod:`tangl.core38.ctx`
        Ambient context helpers for hook propagation.
    """

    templ_hash: str | None = None
    """Optional provenance hash of the template used to materialize this entity."""

    def is_instance(self, obj_cls: type | tuple[type, ...]) -> bool:
        """Legacy alias for ``has_kind``."""
        if isinstance(obj_cls, tuple):
            return all(isinstance(c, type) for c in obj_cls) and isinstance(self, obj_cls)
        return isinstance(obj_cls, type) and isinstance(self, obj_cls)

    def get_tag_kv(self, prefix: str | None = None, enum_type: type | None = None) -> set[Any]:
        """Legacy tag parser for ``key:value`` tags with optional typed coercion."""
        if prefix is None and enum_type is None:
            raise TypeError("Expected at least one of: prefix, enum_type")
        if prefix is None and enum_type in (str, int):
            raise TypeError("prefix is required when enum_type is str or int")

        value_type: type = enum_type or str
        regex = None
        if prefix is not None:
            regex = re.compile(rf"^{re.escape(prefix)}\W(.*)$")

        result: set[Any] = set()
        for tag in self.tags:
            if regex is not None and isinstance(tag, str):
                match = regex.match(tag)
                if not match:
                    continue
                raw: object = match.group(1)
            else:
                raw = tag

            if enum_type is None:
                if isinstance(raw, str):
                    result.add(raw)
                continue

            if issubclass(value_type, Enum):
                try:
                    result.add(value_type(raw))
                except (ValueError, TypeError):
                    continue
            elif value_type is int:
                try:
                    result.add(int(raw))
                except (ValueError, TypeError):
                    continue
            elif value_type is str:
                if isinstance(raw, str):
                    result.add(raw)
            else:
                try:
                    result.add(value_type(raw))
                except Exception:
                    continue

        return result

    def matches(self, *, predicate: Any = None, **criteria: Any) -> bool:
        """Legacy-compatible criteria matcher."""
        from .selector import Selector

        if predicate is not None and not predicate(self):
            return False

        selector_entity = criteria.pop("selector", None)
        if selector_entity is not None:
            get_selection_criteria = getattr(self, "get_selection_criteria", None)
            if callable(get_selection_criteria):
                if not selector_entity.matches(**get_selection_criteria()):
                    return False

        return Selector(**criteria).matches(self)

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

    @classmethod
    def filter_by_criteria(
        cls,
        values: Iterable["Entity"],
        **criteria: Any,
    ) -> Iterator["Entity"]:
        """Legacy bridge: accept both legacy ``matches`` and v38 selectors."""
        from .selector import Selector

        def _matches(value: Entity) -> bool:
            if hasattr(value, "matches"):
                try:
                    return bool(value.matches(**criteria))
                except TypeError:
                    # Fall through to selector semantics if signatures differ.
                    pass
            selector = Selector(**criteria)
            return selector.matches(value)

        return filter(_matches, values)
