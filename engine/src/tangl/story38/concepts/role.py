from __future__ import annotations

from tangl.vm38 import Dependency
from .actor import Actor
from typing import Any, Mapping

from tangl.core38 import Selector
from tangl.vm38 import Dependency, on_get_ns

from ..dispatch import on_gather_ns


class Role(Dependency[Actor]):
    """Role dependency edge (source node -> actor provider)."""

    @staticmethod
    def _invoke_provider_ns(provider: Any, *, ctx: Any = None) -> dict[str, Any]:
        provider_hook = getattr(provider, "on_get_ns", None)
        if not callable(provider_hook):
            return {}

        value = provider_hook(ctx)
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise TypeError(
                f"{type(provider).__name__}.on_get_ns must return Mapping | None"
            )
        return dict(value)

    @on_get_ns
    def on_get_ns(self, ctx) -> dict[str, Any]:
        """Publish role/provider symbols for namespace composition.

        Temporary bridge: ``on_get_ns`` remains transitional until scoped-dispatch
        returns as a first-class mechanism.
        """
        provider = self.provider
        label = self.get_label()
        if provider is None or not label:
            return {}

        payload: dict[str, Any] = {label: provider}

        provider_ns = self._invoke_provider_ns(provider, ctx=ctx)
        for key, value in provider_ns.items():
            payload[f"{label}_{key}"] = value

        return payload


def _role_sort_key(role: Role) -> tuple[str, str]:
    return role.get_label() or "", str(role.uid)


@on_gather_ns
def contribute_roles(*, caller, ctx, **_kw):
    """Inject role providers and role metadata into scoped namespaces."""
    if not hasattr(caller, "edges_out"):
        return None

    contributions: dict[str, Any] = {}
    roles: dict[str, Any] = {}
    role_edges = sorted(caller.edges_out(Selector(has_kind=Role)), key=_role_sort_key)
    for role in role_edges:
        role_payload = role.on_get_ns(ctx)
        if role_payload:
            contributions.update(role_payload)
        provider = role.provider
        label = role.get_label()
        if provider is not None and label:
            roles[label] = provider

    if roles:
        contributions["roles"] = roles

    return contributions or None
