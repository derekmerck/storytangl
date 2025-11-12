from __future__ import annotations

"""Minimal orchestrator for controller endpoint execution."""

from dataclasses import dataclass
import inspect
from typing import Any, Mapping, MutableMapping, TYPE_CHECKING, Union, get_args, get_origin
from uuid import UUID

from .api_endpoint import ApiEndpoint, HasApiEndpoints, MethodType

if TYPE_CHECKING:  # pragma: no cover - import cycles in type checking only
    from tangl.vm.frame import Frame
    from tangl.vm.ledger import Ledger
    from tangl.service.user.user import User


@dataclass
class _CacheEntry:
    """Internal cache record for hydrated resources."""

    resource: Any
    dirty: bool = False


class Orchestrator:
    """Coordinates endpoint execution with lightweight resource hydration."""

    def __init__(self, persistence_manager: Any | None = None) -> None:
        self.persistence = persistence_manager
        self._endpoints: dict[str, tuple[HasApiEndpoints, ApiEndpoint]] = {}
        self._resource_cache: dict[Any, _CacheEntry] = {}

    def register_controller(self, controller: HasApiEndpoints | type[HasApiEndpoints]) -> None:
        instance = controller() if inspect.isclass(controller) else controller
        for name, endpoint in instance.get_api_endpoints().items():
            key = f"{instance.__class__.__name__}.{name}"
            self._endpoints[key] = (instance, endpoint)

    def execute(self, endpoint_name: str, *, user_id: UUID | None = None, **params: Any) -> Any:
        if endpoint_name not in self._endpoints:
            raise KeyError(f"Unknown endpoint: {endpoint_name}")

        controller, endpoint = self._endpoints[endpoint_name]
        self._resource_cache = {}
        resolved_params = self._hydrate_resources(endpoint, user_id, params)
        result = endpoint(controller, **resolved_params)
        result = self._handle_result_cleanup(result)

        if endpoint.method_type in {MethodType.CREATE, MethodType.UPDATE, MethodType.DELETE}:
            for entry in self._resource_cache.values():
                entry.dirty = True
            self._write_back_resources()
        else:
            self._resource_cache.clear()

        return result

    def _hydrate_resources(
        self,
        endpoint: ApiEndpoint,
        user_id: UUID | None,
        params: MutableMapping[str, Any],
    ) -> dict[str, Any]:
        provided = dict(params)
        signature = inspect.signature(endpoint.func)
        func_params = {name for name in signature.parameters if name != "self"}
        resolved = {key: value for key, value in provided.items() if key in func_params}

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
            from tangl.vm.ledger import Ledger

            return Ledger.structure(dict(data))
        raise TypeError("Unsupported ledger payload")

    def _handle_result_cleanup(self, result: Any) -> Any:
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

    def _write_back_resources(self) -> None:
        dirty_items = [entry.resource for entry in self._resource_cache.values() if entry.dirty]
        for resource in dirty_items:
            self._persist_resource(resource)
        self._resource_cache.clear()

    def _persist_resource(self, resource: Any) -> None:
        if self.persistence is None:
            return

        self._call_persistence_save(resource)

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

    def _call_persistence_save(self, payload: Any) -> None:
        saver = getattr(self.persistence, "save", None)
        if callable(saver):
            saver(payload)
            return

        key = getattr(payload, "uid", None)
        if key is None and isinstance(payload, Mapping):
            key = payload.get("uid") or payload.get("ledger_uid")
        if key is None:
            raise ValueError("Unable to determine persistence key for payload")
        self.persistence[key] = payload

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
