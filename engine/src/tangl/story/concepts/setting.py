from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from tangl.core import Selector
from tangl.vm import Dependency

from ..dispatch import on_gather_ns


class Setting(Dependency):
    """Setting()

    Story-specific dependency edge that binds a location provider into local scope.
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

    def provide_setting_symbols(self) -> dict[str, Any]:
        """Publish setting/provider symbols for namespace composition."""
        provider = self.provider
        label = self.get_label()
        if provider is None or not label:
            return {}

        payload: dict[str, Any] = {label: provider}
        provider_ns = self._invoke_provider_ns(provider)
        for key, value in provider_ns.items():
            payload[f"{label}_{key}"] = value
        return payload


def _setting_sort_key(setting: Setting) -> tuple[str, str]:
    return setting.get_label() or "", str(setting.uid)


@on_gather_ns
def contribute_settings(*, caller, ctx, **_kw):
    """Inject setting providers and setting metadata into scoped namespaces."""
    if not hasattr(caller, "edges_out"):
        return None

    scope_nodes = list(caller.ancestors) if hasattr(caller, "ancestors") else [caller]

    contributions: dict[str, Any] = {}
    settings: dict[str, Any] = {}
    for scope in reversed(scope_nodes):
        setting_edges = sorted(scope.edges_out(Selector(has_kind=Setting)), key=_setting_sort_key)
        for setting in setting_edges:
            setting_payload = setting.provide_setting_symbols()
            if setting_payload:
                contributions.update(setting_payload)
            provider = setting.provider
            label = setting.get_label()
            if provider is not None and label:
                settings[label] = provider

    if settings:
        contributions["settings"] = settings

    return contributions or None
