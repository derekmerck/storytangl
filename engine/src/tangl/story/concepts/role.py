from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tangl.core import Selector
from tangl.vm import Dependency

from ..dispatch import on_gather_ns
from .actor import Actor


class Role(Dependency[Actor]):
    """Role()

    Story-specific dependency edge that binds an actor provider into local scope.

    Why
    ----
    ``Role`` turns generic dependency resolution into a narrative concept with a
    stable namespace contract, making resolved actors available under both the
    role label and derived metadata keys.

    Key Features
    ------------
    * Extends :class:`~tangl.vm.provision.requirement.Dependency` so role edges
      participate in standard provisioning and frontier resolution.
    * Publishes the resolved actor under the role label plus derived metadata
      keys such as ``guide_name``.
    * Contributes a merged ``roles`` mapping during namespace gathering.

    API
    ---
    - :meth:`provide_role_symbols` returns the namespace payload contributed by
      the resolved actor.

    See also
    --------
    :class:`Actor`
        Default provider type bound by role dependencies.
    :class:`~tangl.vm.provision.requirement.Dependency`
        Base provisioning edge contract used by story roles.
    """

    @staticmethod
    def _invoke_provider_ns(provider: Any) -> dict[str, Any]:
        get_ns = getattr(provider, "get_ns", None)
        if not callable(get_ns):
            return {}

        value = get_ns()
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise TypeError(
                f"{type(provider).__name__}.get_ns must return Mapping | None",
            )

        payload = dict(value)
        return {key: item for key, item in payload.items() if item is not provider}

    def provide_role_symbols(self) -> dict[str, Any]:
        """Publish role/provider symbols for namespace composition."""
        provider = self.provider
        label = self.get_label()
        if provider is None or not label:
            return {}

        payload: dict[str, Any] = {label: provider}
        provider_ns = self._invoke_provider_ns(provider)
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

    scope_nodes = list(caller.ancestors) if hasattr(caller, "ancestors") else [caller]

    contributions: dict[str, Any] = {}
    roles: dict[str, Any] = {}
    for scope in reversed(scope_nodes):
        role_edges = sorted(scope.edges_out(Selector(has_kind=Role)), key=_role_sort_key)
        for role in role_edges:
            role_payload = role.provide_role_symbols()
            if role_payload:
                contributions.update(role_payload)
            provider = role.provider
            label = role.get_label()
            if provider is not None and label:
                roles[label] = provider

    if roles:
        contributions["roles"] = roles

    return contributions or None
