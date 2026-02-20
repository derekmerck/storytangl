from __future__ import annotations

"""Service38 orchestrator with strict endpoint binding and policy-aware persistence."""

from dataclasses import dataclass
import inspect
from typing import Any, Iterable, Mapping, MutableMapping, TYPE_CHECKING, Union, get_args, get_origin
from uuid import UUID

from pydantic import BaseModel

from tangl.core import BaseFragment
from tangl.service.exceptions import ServiceError

from .api_endpoint import (
    EndpointPolicy,
    LegacyApiEndpoint,
    MethodType,
    PostprocessResult,
    PreprocessResult,
    ResponseType,
    WritebackMode,
)
from .response import (
    InfoModel,
    NativeResponse,
    RuntimeInfo,
    coerce_runtime_info,
)

if TYPE_CHECKING:  # pragma: no cover - import cycles in type checking only
    from tangl.service.api_endpoint import HasApiEndpoints


@dataclass
class _CacheEntry:
    """Internal cache record for hydrated resources."""

    resource: Any
    dirty: bool = False


@dataclass(frozen=True)
class ExecuteOptions:
    """Per-call execution options for service38 orchestration."""

    writeback_mode: WritebackMode | None = None
    persist_paths: tuple[str, ...] | None = None

    def as_policy(self) -> EndpointPolicy | None:
        """Convert options into a policy override object."""

        if self.writeback_mode is None and self.persist_paths is None:
            return None
        return EndpointPolicy(
            writeback_mode=self.writeback_mode or WritebackMode.AUTO,
            persist_paths=tuple(self.persist_paths or ()),
        )


@dataclass
class _EndpointBinding:
    """Internal endpoint binding for orchestrator dispatch."""

    controller: Any
    endpoint: LegacyApiEndpoint
    policy: EndpointPolicy


class Orchestrator38:
    """Coordinates endpoint execution with strict binding and persistence policies."""

    def __init__(self, persistence_manager: Any | None = None) -> None:
        self.persistence = persistence_manager
        self._endpoints: dict[str, _EndpointBinding] = {}
        self._resource_cache: dict[Any, _CacheEntry] = {}

    def register_controller(self, controller: "HasApiEndpoints" | type["HasApiEndpoints"]) -> None:
        """Register controller endpoints for dispatch."""

        instance = controller() if inspect.isclass(controller) else controller
        for name, endpoint in instance.get_api_endpoints().items():
            key = f"{instance.__class__.__name__}.{name}"
            self._endpoints[key] = _EndpointBinding(
                controller=instance,
                endpoint=endpoint,
                policy=EndpointPolicy.from_endpoint(endpoint),
            )

    def set_endpoint_policy(
        self,
        endpoint_name: str,
        *,
        writeback_mode: WritebackMode | None = None,
        persist_paths: Iterable[str] | None = None,
    ) -> None:
        """Override policy for a registered endpoint."""

        binding = self._endpoints.get(endpoint_name)
        if binding is None:
            raise KeyError(f"Unknown endpoint: {endpoint_name}")

        base_policy = binding.policy
        binding.policy = EndpointPolicy(
            writeback_mode=writeback_mode or base_policy.writeback_mode,
            persist_paths=tuple(persist_paths) if persist_paths is not None else base_policy.persist_paths,
        )

    def execute(
        self,
        endpoint_name: str,
        *,
        user_id: UUID | None = None,
        exec_options: ExecuteOptions | None = None,
        **params: Any,
    ) -> NativeResponse:
        """Execute endpoint with service38 policy semantics."""

        binding = self._endpoints.get(endpoint_name)
        if binding is None:
            raise KeyError(f"Unknown endpoint: {endpoint_name}")

        self._resource_cache = {}
        endpoint = binding.endpoint
        policy_override = exec_options.as_policy() if exec_options is not None else None
        policy = binding.policy.merged(policy_override)

        resolved_params = self._hydrate_resources(endpoint, user_id, params)

        try:
            result = self._invoke_endpoint(binding.controller, endpoint, resolved_params)
            result = self._normalize_runtime_result(endpoint, result)
            self._validate_response(endpoint, result)
            result = self._handle_result_cleanup(result)

            persisted_keys: set[Any] = set()

            if self._should_write_back(endpoint.method_type, policy.writeback_mode):
                for entry in self._resource_cache.values():
                    entry.dirty = True
                self._write_back_resources(persisted_keys)
            else:
                self._resource_cache.clear()

            if policy.persist_paths:
                self._persist_from_paths(result, policy.persist_paths, persisted_keys)

            return result

        except ServiceError as exc:
            ledger = resolved_params.get("ledger")
            cursor_id = getattr(ledger, "cursor_id", None)
            step = getattr(ledger, "step", None)
            self._resource_cache.clear()
            return RuntimeInfo.error(
                code=exc.code,
                message=str(exc),
                cursor_id=cursor_id,
                step=step,
            )

    @staticmethod
    def _should_write_back(method_type: MethodType, mode: WritebackMode) -> bool:
        if mode == WritebackMode.ALWAYS:
            return True
        if mode == WritebackMode.NEVER:
            return False
        return method_type in {MethodType.CREATE, MethodType.UPDATE, MethodType.DELETE}

    def _hydrate_resources(
        self,
        endpoint: LegacyApiEndpoint,
        user_id: UUID | None,
        params: MutableMapping[str, Any],
    ) -> dict[str, Any]:
        provided = dict(params)
        resolved = dict(provided)

        explicit_ledger_id = provided.get("ledger_id")
        computed_ledger_id: UUID | None = explicit_ledger_id
        hydrated_ledger: Any | None = resolved.get("ledger") if "ledger" in resolved else None

        hints = {k: v for k, v in endpoint.type_hints().items() if k != "return"}

        for name, annotation in hints.items():
            if name in resolved:
                continue

            if self._is_user_type(annotation):
                if user_id is None:
                    raise ValueError("user_id is required to hydrate user parameter")
                resolved[name] = self._get_or_load_user(user_id)
                continue

            if self._is_ledger_type(annotation):
                ledger_id = explicit_ledger_id if explicit_ledger_id is not None else computed_ledger_id
                if ledger_id is None:
                    ledger_id = self._infer_ledger_id(user_id)
                    computed_ledger_id = ledger_id
                ledger = self._get_or_load_ledger(ledger_id)
                hydrated_ledger = ledger
                resolved[name] = ledger
                continue

            if self._is_frame_type(annotation):
                ledger = hydrated_ledger
                if ledger is None:
                    ledger_id = explicit_ledger_id if explicit_ledger_id is not None else computed_ledger_id
                    if ledger_id is None:
                        ledger_id = self._infer_ledger_id(user_id)
                        computed_ledger_id = ledger_id
                    ledger = self._get_or_load_ledger(ledger_id)
                    hydrated_ledger = ledger
                resolved[name] = ledger.get_frame()

        return resolved

    def _invoke_endpoint(
        self,
        controller: Any,
        endpoint: LegacyApiEndpoint,
        params: dict[str, Any],
    ) -> Any:
        args: tuple[Any, ...] = (controller,)
        kwargs: dict[str, Any] = dict(params)

        for pre in endpoint.preprocessors:
            decision = pre(args, kwargs)

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

        signature = inspect.signature(endpoint.func)
        internal_params = {"user_id", "ledger_id"}
        for internal_name in internal_params:
            if internal_name not in signature.parameters:
                kwargs.pop(internal_name, None)
        try:
            bound = signature.bind(*args, **kwargs)
        except TypeError as exc:
            raise TypeError(f"{endpoint.func.__qualname__} argument binding failed: {exc}") from exc

        result = endpoint.func(*bound.args, **bound.kwargs)

        for post in endpoint.postprocessors:
            decision = post(result)

            if isinstance(decision, PostprocessResult):
                result = decision.result
                if decision.stop:
                    return result
                continue

            if decision is None:
                continue

            result = decision

        return result

    def _infer_ledger_id(self, user_id: UUID | None) -> UUID:
        if user_id is None:
            raise ValueError("ledger_id required when no user context")
        user = self._get_or_load_user(user_id)
        ledger_id = getattr(user, "current_ledger_id", None)
        if ledger_id is None:
            raise ValueError("User has no active ledger")
        return ledger_id

    def _get_or_load_user(self, user_id: UUID) -> Any:
        entry = self._resource_cache.get(user_id)
        if entry is not None:
            return entry.resource

        user = self._fetch_from_persistence(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        self._resource_cache[user_id] = _CacheEntry(user)
        return user

    def _get_or_load_ledger(self, ledger_id: UUID) -> Any:
        entry = self._resource_cache.get(ledger_id)
        if entry is not None:
            return entry.resource

        data = self._fetch_from_persistence(ledger_id)
        if data is None:
            raise ValueError(f"Ledger {ledger_id} not found")

        ledger = self._build_ledger(data)
        self._resource_cache[ledger_id] = _CacheEntry(ledger)
        return ledger

    def _build_ledger(self, data: Any) -> Any:
        if hasattr(data, "get_frame") and hasattr(data, "unstructure"):
            return data
        if isinstance(data, Mapping):
            if (
                "graph" in data
                and "output_stream" in data
                and "cursor_history" in data
            ):
                from tangl.vm38.runtime.ledger import Ledger as Ledger38

                return Ledger38.structure(dict(data))
            from tangl.vm.ledger import Ledger

            return Ledger.structure(dict(data))
        raise TypeError("Unsupported ledger payload")

    def _handle_result_cleanup(self, result: Any) -> Any:
        if isinstance(result, RuntimeInfo):
            details = dict(result.details or {})
            raw_ledger_id = details.pop("_delete_ledger_id", None)
            if raw_ledger_id is None:
                result.details = details or None
                return result

            try:
                ledger_id = UUID(str(raw_ledger_id))
            except (TypeError, ValueError):
                self._update_runtime_details(result, persistence_deleted=False)
                return result

            self._resource_cache.pop(ledger_id, None)
            deleted = self._delete_from_persistence(ledger_id)
            details["persistence_deleted"] = deleted
            result.details = details
            return result

        if not isinstance(result, MutableMapping):
            return result

        raw_ledger_id = result.pop("_delete_ledger_id", None)
        if raw_ledger_id is None:
            return result

        try:
            ledger_id = UUID(str(raw_ledger_id))
        except (TypeError, ValueError):
            result["persistence_deleted"] = False
            return result

        self._resource_cache.pop(ledger_id, None)
        deleted = self._delete_from_persistence(ledger_id)
        result["persistence_deleted"] = deleted
        return result

    def _validate_response(self, endpoint: LegacyApiEndpoint, result: Any) -> None:
        """Ensure controller return type matches declared response type."""

        response_type = getattr(endpoint, "response_type", None)
        if response_type is None:
            return

        if response_type == ResponseType.CONTENT:
            if not isinstance(result, list):
                raise TypeError(
                    f"{endpoint.func.__qualname__} declared ResponseType.CONTENT "
                    f"but returned {type(result).__name__}."
                )
            if result and not all(isinstance(item, BaseFragment) for item in result):
                raise TypeError(
                    f"{endpoint.func.__qualname__} declared ResponseType.CONTENT "
                    "but returned a list with non-BaseFragment items."
                )

        elif response_type == ResponseType.INFO:
            if not isinstance(result, (InfoModel, BaseModel)):
                raise TypeError(
                    f"{endpoint.func.__qualname__} declared ResponseType.INFO "
                    f"but returned {type(result).__name__}, expected InfoModel or BaseModel."
                )

        elif response_type == ResponseType.RUNTIME:
            if not isinstance(result, RuntimeInfo):
                raise TypeError(
                    f"{endpoint.func.__qualname__} declared ResponseType.RUNTIME "
                    f"but returned {type(result).__name__}, expected RuntimeInfo."
                )

        elif response_type == ResponseType.MEDIA:
            return

    @staticmethod
    def _normalize_runtime_result(endpoint: LegacyApiEndpoint, result: Any) -> Any:
        """Coerce runtime-like payloads onto service38-native ``RuntimeInfo``."""

        response_type = getattr(endpoint, "response_type", None)
        if response_type != ResponseType.RUNTIME:
            return result
        return coerce_runtime_info(result) or result

    @staticmethod
    def _update_runtime_details(result: RuntimeInfo, **updates: Any) -> None:
        details = dict(result.details or {})
        details.pop("_delete_ledger_id", None)
        details.update(updates)
        result.details = details

    def _delete_from_persistence(self, ledger_id: UUID) -> bool:
        if self.persistence is None:
            return False

        remover = getattr(self.persistence, "remove", None)
        if callable(remover):
            try:
                remover(ledger_id)
                return True
            except KeyError:
                return False

        try:
            del self.persistence[ledger_id]
            return True
        except KeyError:
            try:
                del self.persistence[str(ledger_id)]
                return True
            except KeyError:
                return False

    def _write_back_resources(self, persisted_keys: set[Any] | None = None) -> None:
        dirty_items = [entry.resource for entry in self._resource_cache.values() if entry.dirty]
        for resource in dirty_items:
            self._persist_resource(resource, persisted_keys)
        self._resource_cache.clear()

    def _persist_resource(self, resource: Any, persisted_keys: set[Any] | None = None) -> None:
        if self.persistence is None:
            return

        self._call_persistence_save(resource, persisted_keys)

    def _persist_from_paths(
        self,
        result: Any,
        paths: Iterable[str],
        persisted_keys: set[Any] | None = None,
    ) -> None:
        if self.persistence is None:
            return

        for path in paths:
            for payload in self._resolve_path_values(result, path):
                self._persist_resource(payload, persisted_keys)

    def _resolve_path_values(self, root: Any, path: str) -> list[Any]:
        if not path:
            return []

        current: Any = root
        for segment in path.split("."):
            if current is None:
                return []
            if isinstance(current, RuntimeInfo):
                if segment == "details":
                    current = dict(current.details or {})
                else:
                    current = getattr(current, segment, None)
                continue
            if isinstance(current, Mapping):
                current = current.get(segment)
                continue
            current = getattr(current, segment, None)

        if current is None:
            return []
        if isinstance(current, (list, tuple, set)):
            return [item for item in current if item is not None]
        return [current]

    def _fetch_from_persistence(self, identifier: Any) -> Any:
        if self.persistence is None:
            raise RuntimeError("Persistence manager required for resource hydration")

        getter = getattr(self.persistence, "get", None)
        if callable(getter):
            return getter(identifier)
        try:
            return self.persistence[identifier]
        except KeyError:
            return None

    def _call_persistence_save(
        self,
        payload: Any,
        persisted_keys: set[Any] | None = None,
    ) -> None:
        key = self._persistence_key(payload)
        if persisted_keys is not None and key is not None and key in persisted_keys:
            return

        saver = getattr(self.persistence, "save", None)
        if callable(saver):
            saver(payload)
            if persisted_keys is not None and key is not None:
                persisted_keys.add(key)
            return

        if key is None:
            raise ValueError("Unable to determine persistence key for payload")

        self.persistence[key] = payload
        if persisted_keys is not None:
            persisted_keys.add(key)

    @staticmethod
    def _persistence_key(payload: Any) -> Any:
        key = getattr(payload, "uid", None)
        if key is None and isinstance(payload, Mapping):
            key = payload.get("uid") or payload.get("ledger_uid")
        return key

    def _is_user_type(self, annotation: Any) -> bool:
        resolved = self._resolve_annotation(annotation)
        name = getattr(resolved, "__name__", "")
        return name.endswith("User")

    def _is_ledger_type(self, annotation: Any) -> bool:
        resolved = self._resolve_annotation(annotation)
        name = getattr(resolved, "__name__", "")
        return name.endswith("Ledger")

    def _is_frame_type(self, annotation: Any) -> bool:
        resolved = self._resolve_annotation(annotation)
        name = getattr(resolved, "__name__", "")
        return name.endswith("Frame")

    def _resolve_annotation(self, annotation: Any) -> Any:
        origin = get_origin(annotation)
        if origin is None:
            return annotation
        if origin is Union:
            args = [arg for arg in get_args(annotation) if arg is not type(None)]
            if len(args) == 1:
                return self._resolve_annotation(args[0])
        return annotation


__all__ = [
    "ExecuteOptions",
    "Orchestrator38",
    "WritebackMode",
]
