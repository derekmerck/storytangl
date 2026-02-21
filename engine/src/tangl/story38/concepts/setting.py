from __future__ import annotations

from typing import Any, Mapping

from tangl.core38 import Selector
from tangl.vm38 import Dependency, on_get_ns

from ..dispatch import on_gather_ns


class Setting(Dependency):
    """Setting dependency edge (source node -> location provider)."""

    @staticmethod
    def _invoke_provider_ns(provider: Any, *, ctx: Any = None) -> dict[str, Any]:
        provider_hook = getattr(provider, "on_get_ns", None)
        if not callable(provider_hook):
            return {}
        try:
            value = provider_hook(ctx)
        except TypeError:
            try:
                value = provider_hook(provider, ctx)
            except TypeError:
                value = provider_hook()
        if value is None:
            return {}
        if isinstance(value, Mapping):
            return dict(value)
        return dict(value)

    @on_get_ns
    def on_get_ns(self, ctx) -> dict[str, Any]:
        """Publish setting/provider symbols for namespace composition.

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


def _setting_sort_key(setting: Setting) -> tuple[str, str]:
    return setting.get_label() or "", str(setting.uid)


@on_gather_ns
def contribute_settings(*, caller, ctx, **_kw):
    """Inject setting providers and setting metadata into scoped namespaces."""
    if not hasattr(caller, "edges_out"):
        return None

    contributions: dict[str, Any] = {}
    settings: dict[str, Any] = {}
    setting_edges = sorted(caller.edges_out(Selector(has_kind=Setting)), key=_setting_sort_key)
    for setting in setting_edges:
        setting_payload = setting.on_get_ns(ctx)
        if setting_payload:
            contributions.update(setting_payload)
        provider = setting.provider
        label = setting.get_label()
        if provider is not None and label:
            settings[label] = provider

    if settings:
        contributions["settings"] = settings

    return contributions or None
