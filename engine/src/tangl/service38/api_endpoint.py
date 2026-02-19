"""Service38 endpoint metadata and compatibility wrappers."""

from __future__ import annotations

from enum import Enum
import functools
from typing import Any, Callable

from pydantic import BaseModel, Field

from tangl.service.api_endpoint import (
    AccessLevel,
    ApiEndpoint as LegacyApiEndpoint,
    HasApiEndpoints,
    MethodType,
    PostprocessResult,
    PreprocessResult,
    ResponseType,
)


class WritebackMode(str, Enum):
    """Writeback strategy for orchestrator execution."""

    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


class EndpointPolicy(BaseModel):
    """Persistence policy attached to service endpoints."""

    writeback_mode: WritebackMode = WritebackMode.AUTO
    persist_paths: tuple[str, ...] = Field(default_factory=tuple)

    def merged(self, other: "EndpointPolicy | None") -> "EndpointPolicy":
        """Merge runtime overrides over endpoint defaults."""

        if other is None:
            return self

        mode = other.writeback_mode if other.writeback_mode is not None else self.writeback_mode
        paths = other.persist_paths if other.persist_paths else self.persist_paths
        return EndpointPolicy(writeback_mode=mode, persist_paths=tuple(paths))

    @classmethod
    def from_endpoint(cls, endpoint: LegacyApiEndpoint) -> "EndpointPolicy":
        """Extract policy fields from an endpoint instance when present."""

        mode_raw = getattr(endpoint, "writeback_mode", WritebackMode.AUTO)
        try:
            mode = mode_raw if isinstance(mode_raw, WritebackMode) else WritebackMode(str(mode_raw))
        except ValueError:
            mode = WritebackMode.AUTO

        raw_paths = getattr(endpoint, "persist_paths", ()) or ()
        return cls(writeback_mode=mode, persist_paths=tuple(str(path) for path in raw_paths))


class ApiEndpoint38(LegacyApiEndpoint):
    """Service38 endpoint type with policy metadata."""

    writeback_mode: WritebackMode = WritebackMode.AUTO
    persist_paths: tuple[str, ...] = Field(default_factory=tuple)

    @classmethod
    def annotate(
        cls,
        name: str = None,
        group: str = None,
        method_type: MethodType = None,
        response_type: ResponseType = None,
        access_level: AccessLevel = None,
        preprocessors: list | None = None,
        postprocessors: list | None = None,
        writeback_mode: WritebackMode = WritebackMode.AUTO,
        persist_paths: tuple[str, ...] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator that records service38 policy metadata on endpoint methods."""

        persist_paths = tuple(persist_paths or ())

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            endpoint = cls(
                func=func,
                name=name,
                group=group,
                method_type=method_type,
                response_type=response_type,
                access_level=access_level,
                preprocessors=preprocessors,
                postprocessors=postprocessors,
                writeback_mode=writeback_mode,
                persist_paths=persist_paths,
            )

            @functools.wraps(func)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                return endpoint(*args, **kwargs)
            wrapped._api_endpoint = endpoint
            return wrapped

        return decorator


__all__ = [
    "AccessLevel",
    "ApiEndpoint38",
    "EndpointPolicy",
    "HasApiEndpoints",
    "LegacyApiEndpoint",
    "MethodType",
    "PostprocessResult",
    "PreprocessResult",
    "ResponseType",
    "WritebackMode",
]
