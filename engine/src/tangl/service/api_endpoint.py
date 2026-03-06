"""Service38 endpoint metadata and compatibility wrappers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
import functools
import inspect
from typing import Any, Callable, Mapping, get_type_hints

from pydantic import BaseModel, Field, model_validator

class AccessLevel(IntEnum):
    PUBLIC = 10
    USER = 50
    RESTRICTED = 100


class MethodType(Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

    def http_verb(self) -> str:
        mapping = {
            MethodType.CREATE: "POST",
            MethodType.READ: "GET",
            MethodType.UPDATE: "POST",
            MethodType.DELETE: "DELETE",
        }
        return mapping[self]


class ResponseType(Enum):
    CONTENT = "content"
    INFO = "info"
    RUNTIME = "runtime"
    MEDIA = "media"


@dataclass(frozen=True)
class PreprocessResult:
    args: tuple[Any, ...] | None = None
    kwargs: Mapping[str, Any] | None = None
    skip_main: bool = False
    result: Any = None

    @classmethod
    def skip(cls, result: Any = None) -> "PreprocessResult":
        return cls(args=None, kwargs=None, skip_main=True, result=result)


@dataclass(frozen=True)
class PostprocessResult:
    result: Any
    stop: bool = False

    @classmethod
    def stop_with(cls, result: Any) -> "PostprocessResult":
        return cls(result=result, stop=True)


class LegacyApiEndpoint(BaseModel):
    func: Callable
    name: str
    group: str
    method_type: MethodType
    response_type: ResponseType
    access_level: AccessLevel = AccessLevel.RESTRICTED
    preprocessors: list = Field(default_factory=list)
    postprocessors: list = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _infer_metadata_fields(cls, data: Mapping[str, Any]) -> Mapping[str, Any]:
        payload = dict(data)
        func = payload.get("func")

        if payload.get("name") is None and func is not None:
            payload["name"] = func.__name__

        if payload.get("group") is None and func is not None:
            parts = func.__qualname__.split(".")
            if len(parts) > 1:
                payload["group"] = parts[-2].replace("Controller", "").lower()

        if payload.get("method_type") is None:
            name = payload.get("name")
            if name is None:
                raise ValueError("Cannot infer method_type: name is missing.")
            if name.startswith("get_"):
                payload["method_type"] = MethodType.READ
            elif name.startswith("create_") or name.startswith("load_"):
                payload["method_type"] = MethodType.CREATE
            elif name.startswith("drop_") or name.startswith("unload_"):
                payload["method_type"] = MethodType.DELETE
            elif name.startswith("update_") or name.startswith("do_") or name.startswith("resolve_"):
                payload["method_type"] = MethodType.UPDATE
            else:
                raise ValueError(f"Unable to infer method type from: {name}")

        if payload.get("response_type") is None:
            method_type = payload["method_type"]
            name = payload["name"]
            if method_type in (MethodType.CREATE, MethodType.DELETE, MethodType.UPDATE):
                payload["response_type"] = ResponseType.RUNTIME
            else:
                if "info" in name:
                    payload["response_type"] = ResponseType.INFO
                elif "content" in name:
                    payload["response_type"] = ResponseType.CONTENT
                elif "media" in name:
                    payload["response_type"] = ResponseType.MEDIA
                else:
                    raise ValueError(f"Unable to infer response type from: {name}")

        payload = {key: value for key, value in payload.items() if value is not None}
        return payload

    def type_hints(self) -> dict[str, Any]:
        return get_type_hints(self.func)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        for preprocessor in self.preprocessors:
            decision = preprocessor(args, kwargs)
            if isinstance(decision, PreprocessResult):
                if decision.args is not None:
                    args = tuple(decision.args)
                if decision.kwargs is not None:
                    kwargs = dict(decision.kwargs)
                if decision.skip_main:
                    return decision.result
                continue

            if decision is None:
                continue

            try:
                args, kwargs = decision
            except (TypeError, ValueError) as exc:
                raise TypeError(
                    "Preprocessor must return (args, kwargs) or PreprocessResult"
                ) from exc

        result = self.func(*args, **kwargs)
        for postprocessor in self.postprocessors:
            decision = postprocessor(result)
            if isinstance(decision, PostprocessResult):
                result = decision.result
                if decision.stop:
                    return result
                continue
            if decision is None:
                result = None
            else:
                result = decision

        return result

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
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
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
            )

            @functools.wraps(func)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                return endpoint(*args, **kwargs)

            wrapped._api_endpoint = endpoint
            return wrapped

        return decorator


class HasApiEndpoints:
    @classmethod
    def get_api_endpoints(cls) -> dict[str, LegacyApiEndpoint]:
        endpoints: dict[str, LegacyApiEndpoint] = {}
        for name, method in inspect.getmembers(cls, predicate=callable):
            endpoint_method = getattr(method, "_api_endpoint", None)
            if isinstance(endpoint_method, LegacyApiEndpoint):
                endpoints[name] = endpoint_method
        return endpoints


class WritebackMode(str, Enum):
    """Writeback strategy for orchestrator execution."""

    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


class ResourceBinding(str, Enum):
    """Hydration bindings supported by service38 orchestrator."""

    USER = "user"
    LEDGER = "ledger"
    FRAME = "frame"


class EndpointPolicy(BaseModel):
    """Persistence policy attached to service endpoints."""

    writeback_mode: WritebackMode = WritebackMode.AUTO
    persist_paths: tuple[str, ...] = Field(default_factory=tuple)

    def merged(self, other: "EndpointPolicy | None") -> "EndpointPolicy":
        if other is None:
            return self
        mode = other.writeback_mode if other.writeback_mode is not None else self.writeback_mode
        paths = other.persist_paths if other.persist_paths else self.persist_paths
        return EndpointPolicy(writeback_mode=mode, persist_paths=tuple(paths))

    @classmethod
    def from_endpoint(cls, endpoint: LegacyApiEndpoint) -> "EndpointPolicy":
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
    binds: tuple[ResourceBinding, ...] | None = None

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
        binds: tuple[ResourceBinding | str, ...] | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        persist_paths = tuple(persist_paths or ())
        normalized_binds: tuple[ResourceBinding, ...] | None
        if binds is None:
            normalized_binds = None
        else:
            normalized_binds = tuple(
                binding if isinstance(binding, ResourceBinding) else ResourceBinding(str(binding).strip().lower())
                for binding in binds
            )

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
                binds=normalized_binds,
            )

            @functools.wraps(func)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                return endpoint(*args, **kwargs)

            wrapped._api_endpoint = endpoint
            return wrapped

        return decorator


ApiEndpoint = ApiEndpoint38


__all__ = [
    "AccessLevel",
    "ApiEndpoint",
    "ApiEndpoint38",
    "EndpointPolicy",
    "HasApiEndpoints",
    "LegacyApiEndpoint",
    "MethodType",
    "PostprocessResult",
    "PreprocessResult",
    "ResourceBinding",
    "ResponseType",
    "WritebackMode",
]
