from __future__ import annotations

"""Gateway-level inbound/outbound hook registries for service38."""

from enum import Enum
import re
from typing import Any, Callable, Iterable

from markdown_it import MarkdownIt
from pydantic import BaseModel

from tangl.core38 import BehaviorRegistry, CallReceipt, DispatchLayer, Priority

from .operations import ServiceOperation38


class HookPhase(str, Enum):
    """Execution phases for gateway hook pipelines."""

    EARLY = "early"
    NORMAL = "normal"
    LATE = "late"


def _normalize_profile_tokens(render_profile: str | Iterable[str] | None) -> set[str]:
    if render_profile is None:
        return {"raw"}
    if isinstance(render_profile, str):
        chunks = [part.strip().lower() for part in re.split(r"[+,]", render_profile) if part.strip()]
        return set(chunks) or {"raw"}
    return {str(token).strip().lower() for token in render_profile if str(token).strip()} or {"raw"}


def _profile_has(render_profile: str | Iterable[str] | None, token: str) -> bool:
    tokens = _normalize_profile_tokens(render_profile)
    return token.lower() in tokens


class GatewayHooks:
    """Behavior-dispatch backed inbound/outbound hook registry."""

    def __init__(self) -> None:
        self._registry = BehaviorRegistry(default_dispatch_layer=DispatchLayer.APPLICATION)
        self._markdown = MarkdownIt()

    def register_inbound(
        self,
        phase: HookPhase,
        *,
        priority: Priority = Priority.NORMAL,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register an inbound params hook for ``phase``."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._registry.register(func=func, task=f"inbound.{phase.value}", priority=priority)
            return func

        return decorator

    def register_outbound(
        self,
        phase: HookPhase,
        *,
        priority: Priority = Priority.NORMAL,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Register an outbound result hook for ``phase``."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._registry.register(func=func, task=f"outbound.{phase.value}", priority=priority)
            return func

        return decorator

    def run_inbound(
        self,
        params: dict[str, Any],
        *,
        operation: ServiceOperation38,
        render_profile: str | Iterable[str] | None,
        user_id: Any,
    ) -> dict[str, Any]:
        """Run inbound hooks through early/normal/late phases."""

        current: dict[str, Any] = dict(params)
        for phase in (HookPhase.EARLY, HookPhase.NORMAL, HookPhase.LATE):
            receipts = list(
                self._registry.execute_all(
                    task=f"inbound.{phase.value}",
                    call_args=(current,),
                    call_kwargs={
                        "operation": operation,
                        "render_profile": render_profile,
                        "user_id": user_id,
                    },
                )
            )
            updated = CallReceipt.last_result(*receipts)
            if isinstance(updated, dict):
                current = updated
        return current

    def run_outbound(
        self,
        result: Any,
        *,
        operation: ServiceOperation38,
        render_profile: str | Iterable[str] | None,
        user_id: Any,
    ) -> Any:
        """Run outbound hooks through early/normal/late phases."""

        current = result
        for phase in (HookPhase.EARLY, HookPhase.NORMAL, HookPhase.LATE):
            receipts = list(
                self._registry.execute_all(
                    task=f"outbound.{phase.value}",
                    call_args=(current,),
                    call_kwargs={
                        "operation": operation,
                        "render_profile": render_profile,
                        "user_id": user_id,
                    },
                )
            )
            updated = CallReceipt.last_result(*receipts)
            if updated is not None:
                current = updated
        return current

    def install_default_hooks(self) -> None:
        """Install built-in outbound transforms used by service38."""

        @self.register_inbound(HookPhase.NORMAL, priority=Priority.NORMAL)
        def _normalize_story38_init_mode(
            params: dict[str, Any],
            *,
            operation: ServiceOperation38,
            **_: Any,
        ) -> dict[str, Any]:
            if operation != ServiceOperation38.STORY38_CREATE:
                return params
            init_mode = params.get("init_mode")
            if isinstance(init_mode, str):
                params = dict(params)
                params["init_mode"] = init_mode.strip().lower()
            return params

        @self.register_outbound(HookPhase.NORMAL, priority=Priority.NORMAL)
        def _html_transform(payload: Any, *, render_profile: str | Iterable[str] | None, **_: Any) -> Any:
            if not _profile_has(render_profile, "html"):
                return payload
            return self._transform_text_fields(payload, self._markdown.render)

        @self.register_outbound(HookPhase.LATE, priority=Priority.LATE)
        def _media_url_transform(payload: Any, *, render_profile: str | Iterable[str] | None, **_: Any) -> Any:
            if not _profile_has(render_profile, "media_url"):
                return payload
            return self._transform_media_fields(payload)

        @self.register_outbound(HookPhase.LATE, priority=Priority.LAST)
        def _cli_ascii_transform(payload: Any, *, render_profile: str | Iterable[str] | None, **_: Any) -> Any:
            if not _profile_has(render_profile, "cli_ascii"):
                return payload
            return self._transform_media_to_ascii(payload)

    def _transform_text_fields(self, value: Any, text_transform: Callable[[str], str]) -> Any:
        if isinstance(value, str):
            return text_transform(value)
        if isinstance(value, list):
            return [self._transform_text_fields(item, text_transform) for item in value]
        if isinstance(value, dict):
            transformed: dict[str, Any] = {}
            for key, item in value.items():
                if key in {"text", "content"} and isinstance(item, str):
                    transformed[key] = text_transform(item)
                else:
                    transformed[key] = self._transform_text_fields(item, text_transform)
            return transformed
        if isinstance(value, BaseModel):
            data = value.model_dump(mode="python")
            transformed = self._transform_text_fields(data, text_transform)
            if isinstance(transformed, dict):
                return value.model_copy(update=transformed)
            return value
        if hasattr(value, "text") and isinstance(getattr(value, "text", None), str):
            try:
                value.text = text_transform(value.text)
            except Exception:
                pass
        if hasattr(value, "content") and isinstance(getattr(value, "content", None), str):
            try:
                value.content = text_transform(value.content)
            except Exception:
                pass
        return value

    def _transform_media_fields(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._transform_media_fields(item) for item in value]
        if isinstance(value, dict):
            transformed: dict[str, Any] = {
                key: self._transform_media_fields(item) for key, item in value.items()
            }
            if transformed.get("fragment_type") == "media" and "url" not in transformed:
                scope = transformed.get("scope") or "world"
                label = transformed.get("label") or transformed.get("source_label") or "media"
                transformed["url"] = f"/media/{scope}/{label}"
            return transformed
        if isinstance(value, BaseModel):
            data = value.model_dump(mode="python")
            transformed = self._transform_media_fields(data)
            if isinstance(transformed, dict):
                return value.model_copy(update=transformed)
            return value
        return value

    def _transform_media_to_ascii(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._transform_media_to_ascii(item) for item in value]
        if isinstance(value, dict):
            if value.get("fragment_type") == "media":
                label = value.get("label") or value.get("source_label") or value.get("url") or "media"
                text = value.get("text") or ""
                return f"[media] {label} {text}".strip()
            return {key: self._transform_media_to_ascii(item) for key, item in value.items()}
        if isinstance(value, BaseModel):
            data = value.model_dump(mode="python")
            transformed = self._transform_media_to_ascii(data)
            if isinstance(transformed, dict):
                return value.model_copy(update=transformed)
            return transformed
        return value


__all__ = [
    "GatewayHooks",
    "HookPhase",
]
