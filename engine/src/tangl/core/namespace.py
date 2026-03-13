"""Namespace contribution helpers for v38 entities.

This module defines a small, explicit contract for entity-local namespace
publication:

- mark fields or methods with ``contribute_ns`` metadata;
- call ``get_ns()`` to collect only this entity's local namespace maps.

The contract is intentionally instance-bound and dispatch-free. Runtime layers
assemble scoped namespaces later (for example caller + ancestors + world) via
their own dispatch hooks.
"""

from __future__ import annotations

from collections import ChainMap
from collections.abc import Mapping
from typing import Any, Callable

from .bases import BaseModelPlus

__all__ = ["HasNamespace", "contribute_ns"]


def contribute_ns(func: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a method as a namespace contributor."""
    setattr(func, "contribute_ns", True)
    return func


class HasNamespace(BaseModelPlus):
    """Mixin providing instance-local namespace publication."""

    @staticmethod
    def _as_mapping(name: str, value: Any) -> Mapping[str, Any]:
        if value is None:
            return {}
        if isinstance(value, Mapping):
            return value
        return {name: value}

    @contribute_ns
    def provide_myself_by_identifiers(self) -> Mapping[str, Any]:
        """Bind this entity by stable self/identifier aliases."""
        payload: dict[str, Any] = {"self": self}

        label = getattr(self, "label", None)
        if isinstance(label, str) and label:
            payload[label] = self

        path = getattr(self, "path", None)
        if isinstance(path, str) and path:
            payload[path] = self

        get_identifiers = getattr(self, "get_identifiers", None)
        if callable(get_identifiers):
            for identifier in get_identifiers() or ():
                key = str(identifier)
                if key:
                    payload[key] = self

        return payload

    def get_ns(self) -> ChainMap[str, Any]:
        """Return only this entity's local namespace contribution maps.

        Runtime layers assemble scoped views later via ``do_gather_ns`` /
        ``ctx.get_ns(node)``; this method does not walk ancestors or consult
        dispatch handlers.
        """
        maps: list[Mapping[str, Any]] = []

        for name in type(self)._match_fields(contribute_ns=True):
            value = getattr(self, name)
            layer = self._as_mapping(name, value)
            if layer:
                maps.append(layer)

        seen_method_names: set[str] = set()
        for cls_ in type(self).__mro__:
            for name, raw in cls_.__dict__.items():
                if name in seen_method_names:
                    continue
                if not callable(raw):
                    continue
                if not getattr(raw, "contribute_ns", False):
                    continue
                seen_method_names.add(name)
                bound = getattr(self, name)
                layer = self._as_mapping(name, bound())
                if layer:
                    maps.append(layer)

        return ChainMap(*maps)
