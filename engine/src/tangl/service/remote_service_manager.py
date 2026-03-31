"""Remote-backed service-manager adapter over the current REST API."""

from __future__ import annotations

import logging
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import UUID

import requests
from pydantic import ValidationError as PydanticValidationError

from tangl.core import BaseFragment
from tangl.journal.fragments import (
    AttributedFragment,
    BlockFragment,
    ChoiceFragment,
    ContentFragment,
    ControlFragment,
    DialogFragment,
    GroupFragment,
    KvFragment,
    MediaFragment,
    UserEventFragment,
)
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.persistence import PersistenceManager
from tangl.type_hints import Identifier, UnstructuredData

from .auth import UserAuthInfo
from .exceptions import (
    AccessDeniedError,
    AuthMismatchError,
    InvalidOperationError,
    ResourceNotFoundError,
    ServiceError,
    ValidationError,
)
from .response import (
    ProjectedState,
    RuntimeEnvelope,
    RuntimeInfo,
    SystemInfo,
    UserInfo,
    UserSecret,
    WorldInfo,
)
from .service_manager import ServiceManager, ServiceSession
from .service_method import BlockingMode, ServiceAccess, ServiceContext, ServiceWriteback, service_method


logger = logging.getLogger(__name__)

_STANDARD_RUNTIME_INFO_FIELDS = {
    "status",
    "code",
    "message",
    "cursor_id",
    "step",
    "details",
}
_KNOWN_FRAGMENT_TYPES: dict[str, type[BaseFragment]] = {
    "attributed": AttributedFragment,
    "block": BlockFragment,
    "choice": ChoiceFragment,
    "content": ContentFragment,
    "delete": ControlFragment,
    "dialog": DialogFragment,
    "group": GroupFragment,
    "kv": KvFragment,
    "media": MediaFragment,
    "update": ControlFragment,
    "user_event": UserEventFragment,
}


class RemoteServiceManager(ServiceManager):
    """Service-manager adapter that fulfills calls through the REST API."""

    def __init__(
        self,
        api_url: str,
        *,
        persistence_manager: PersistenceManager | None = None,
        api_key: str | None = None,
        secret: str | None = None,
        timeout_s: float = 5.0,
        session: requests.Session | None = None,
    ) -> None:
        super().__init__(persistence_manager)

        normalized_url = api_url.strip().rstrip("/")
        if not normalized_url:
            raise ValidationError("Remote service manager requires a non-empty api_url")

        try:
            normalized_timeout = float(timeout_s)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Remote service manager timeout_s must be numeric") from exc
        if normalized_timeout <= 0:
            raise ValidationError("Remote service manager timeout_s must be greater than zero")

        self.api_url = normalized_url
        self.timeout_s = normalized_timeout
        self.session = session or requests.Session()
        self._bound_api_key = api_key.strip() if isinstance(api_key, str) and api_key.strip() else None
        self._bound_secret = secret.strip() if isinstance(secret, str) and secret.strip() else None
        self._bound_user_id: UUID | None = None

    def _auth_headers(self, *, required: bool) -> dict[str, str]:
        api_key = self._ensure_bound_auth()
        if api_key is None:
            if required:
                raise AccessDeniedError("Remote service manager has no bound API key")
            return {}
        return {
            "X-API-Key": api_key,
            "api-key": api_key,
        }

    def _ensure_bound_auth(self) -> str | None:
        if self._bound_api_key:
            return self._bound_api_key
        if self._bound_secret is None:
            return None

        payload = self._request(
            "GET",
            "/system/secret",
            params={"secret": self._bound_secret},
            auth_required=False,
        )
        secret_info = self._decode_model(UserSecret, payload, label="user secret")
        self._bound_api_key = secret_info.api_key
        return self._bound_api_key

    def _check_bound_user(self, user_id: UUID | None) -> None:
        if user_id is None or self._bound_user_id is None:
            return
        if user_id != self._bound_user_id:
            raise AuthMismatchError(
                f"user_id {user_id} does not match remote authenticated user {self._bound_user_id}",
            )

    def _bind_auth_from_secret(self, secret_info: UserSecret) -> None:
        self._bound_api_key = secret_info.api_key
        self._bound_secret = secret_info.user_secret
        if secret_info.user_id is not None:
            self._bound_user_id = secret_info.user_id

    def _request(
        self,
        method: str,
        path: str,
        *,
        auth_required: bool,
        params: Mapping[str, object] | None = None,
        json_body: object | None = None,
    ) -> object:
        request_params = dict(params or {})
        request_params.setdefault("render_profile", "raw")
        url = f"{self.api_url}/{path.lstrip('/')}"
        auth_mode = "anonymous"
        if auth_required:
            headers = self._auth_headers(required=True)
            if self._bound_api_key is not None:
                auth_mode = "api_key"
            elif self._bound_secret is not None:
                auth_mode = "secret_derived"
        else:
            headers: dict[str, str] = {}

        start = perf_counter()
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=request_params or None,
                json=json_body,
                headers=headers or None,
                timeout=self.timeout_s,
            )
        except requests.RequestException as exc:
            logger.warning(
                "Remote service request failed",
                extra={"method": method, "url": url, "auth_mode": auth_mode},
            )
            raise ServiceError(f"Remote service request failed: {exc}") from exc

        latency_ms = round((perf_counter() - start) * 1000, 2)
        try:
            payload = response.json()
        except ValueError as exc:
            logger.warning(
                "Remote service returned invalid JSON",
                extra={
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                },
            )
            raise ServiceError("Remote service returned invalid JSON") from exc

        logger.debug(
            "Remote service request completed",
            extra={
                "method": method,
                "url": url,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "auth_mode": auth_mode,
            },
        )

        if 200 <= response.status_code < 300:
            return payload

        detail = self._payload_detail(payload) or response.reason or "Remote service request failed"
        if response.status_code in {400, 422}:
            raise InvalidOperationError(detail)
        if response.status_code in {401, 403}:
            raise AccessDeniedError(detail)
        if response.status_code == 404:
            raise ResourceNotFoundError(detail)
        raise ServiceError(detail)

    @staticmethod
    def _payload_detail(payload: object) -> str | None:
        if not isinstance(payload, Mapping):
            return None
        detail = payload.get("detail")
        if isinstance(detail, str) and detail:
            return detail
        message = payload.get("message")
        if isinstance(message, str) and message:
            return message
        return None

    @staticmethod
    def _decode_model(model_type: type[Any], payload: object, *, label: str) -> Any:
        try:
            return model_type.model_validate(payload)
        except PydanticValidationError as exc:
            raise ServiceError(f"Remote service returned invalid {label} payload") from exc

    def _decode_fragment(self, payload: object) -> BaseFragment:
        if not isinstance(payload, Mapping):
            return BaseFragment(fragment_type="unknown", content=payload)

        raw_fragment = dict(payload)
        fragment_type = raw_fragment.get("fragment_type")
        if not isinstance(fragment_type, str) or not fragment_type:
            return BaseFragment(fragment_type="unknown", content=raw_fragment)

        fragment_model = _KNOWN_FRAGMENT_TYPES.get(fragment_type)
        if fragment_model is None:
            return BaseFragment(fragment_type=fragment_type, content=raw_fragment)

        try:
            return fragment_model.model_validate(raw_fragment)
        except PydanticValidationError as exc:
            raise ServiceError(
                f"Remote service returned invalid {fragment_type} fragment payload",
            ) from exc

    def _decode_runtime_envelope(self, payload: object) -> RuntimeEnvelope:
        if not isinstance(payload, Mapping):
            raise ServiceError("Remote service returned invalid runtime envelope payload")

        raw_fragments = payload.get("fragments")
        if not isinstance(raw_fragments, list):
            raise ServiceError("Remote service returned runtime envelope without fragment list")

        fragments = [self._decode_fragment(fragment) for fragment in raw_fragments]
        envelope_payload = {
            "cursor_id": payload.get("cursor_id"),
            "step": payload.get("step"),
            "fragments": fragments,
            "last_redirect": payload.get("last_redirect"),
            "redirect_trace": payload.get("redirect_trace") or [],
            "metadata": dict(payload.get("metadata") or {}),
        }
        return self._decode_model(RuntimeEnvelope, envelope_payload, label="runtime envelope")

    def _decode_runtime_info(self, payload: object) -> RuntimeInfo:
        if not isinstance(payload, Mapping):
            raise ServiceError("Remote service returned invalid runtime info payload")

        raw_payload = dict(payload)
        details = raw_payload.get("details")
        if details is None:
            merged_details: dict[str, object] = {}
        elif isinstance(details, Mapping):
            merged_details = dict(details)
        else:
            raise ServiceError("Remote service returned invalid runtime info details payload")

        extra_details = {
            key: value
            for key, value in raw_payload.items()
            if key not in _STANDARD_RUNTIME_INFO_FIELDS
        }
        merged_details.update(extra_details)

        runtime_payload = {
            "status": raw_payload.get("status"),
            "code": raw_payload.get("code"),
            "message": raw_payload.get("message"),
            "cursor_id": raw_payload.get("cursor_id"),
            "step": raw_payload.get("step"),
        }
        if merged_details:
            runtime_payload["details"] = merged_details
        return self._decode_model(RuntimeInfo, runtime_payload, label="runtime info")

    @staticmethod
    def _reject_unexpected_kwargs(
        method_name: str,
        kwargs: Mapping[str, Any],
        *,
        allowed: set[str],
    ) -> None:
        unexpected = sorted(key for key in kwargs if key not in allowed)
        if unexpected:
            names = ", ".join(unexpected)
            raise InvalidOperationError(
                f"Remote {method_name} does not support arguments: {names}",
            )

    @staticmethod
    def _require_non_empty_secret(secret: str | None, *, method_name: str) -> str:
        if not isinstance(secret, str) or not secret.strip():
            raise ValidationError(f"Remote {method_name} requires a non-empty secret")
        return secret.strip()

    def _unsupported(self, name: str) -> InvalidOperationError:
        return InvalidOperationError(f"{name} is not supported by RemoteServiceManager v1")

    @contextmanager
    def open_user(
        self,
        user_id: UUID,
        *,
        write_back: bool = False,
    ) -> Iterator[Any]:
        _ = (user_id, write_back)
        raise self._unsupported("open_user")
        yield  # pragma: no cover

    @contextmanager
    def open_ledger(
        self,
        ledger_id: UUID,
        *,
        write_back: bool = False,
    ) -> Iterator[Any]:
        _ = (ledger_id, write_back)
        raise self._unsupported("open_ledger")
        yield  # pragma: no cover

    @contextmanager
    def open_session(
        self,
        *,
        user_id: UUID | None = None,
        ledger_id: UUID | None = None,
        write_back: bool = False,
        user_auth: UserAuthInfo | None = None,
    ) -> Iterator[ServiceSession]:
        _ = (user_id, ledger_id, write_back, user_auth)
        raise self._unsupported("open_session")
        yield  # pragma: no cover

    def open_world(self, world_id: str, /) -> Any:
        _ = world_id
        raise self._unsupported("open_world")

    @service_method(
        access=ServiceAccess.CLIENT,
        context=ServiceContext.USER,
        writeback=ServiceWriteback.SESSION,
        operation_id="story.create",
    )
    def create_story(
        self,
        *,
        user_id: UUID,
        world_id: str,
        user_auth: UserAuthInfo | None = None,
        **kwargs: Any,
    ) -> RuntimeEnvelope:
        self._validate_user_auth(user_id=user_id, user_auth=user_auth)
        self._check_bound_user(user_id)
        self._reject_unexpected_kwargs(
            "create_story",
            kwargs,
            allowed={"init_mode", "mode", "story_label"},
        )

        params: dict[str, object] = {"world_id": world_id}
        if kwargs.get("story_label") is not None:
            params["story_label"] = kwargs["story_label"]
        mode_value = kwargs.get("init_mode", kwargs.get("mode"))
        if mode_value is not None:
            params["init_mode"] = str(mode_value)

        payload = self._request(
            "POST",
            "/story/story/create",
            auth_required=True,
            params=params,
        )
        return self._decode_runtime_envelope(payload)

    @service_method(
        access=ServiceAccess.CLIENT,
        context=ServiceContext.SESSION,
        writeback=ServiceWriteback.SESSION,
        operation_id="story.do",
    )
    def resolve_choice(
        self,
        *,
        choice_id: UUID,
        user_id: UUID | None = None,
        ledger_id: UUID | None = None,
        user_auth: UserAuthInfo | None = None,
        choice_payload: Any = None,
    ) -> RuntimeEnvelope:
        self._validate_user_auth(user_id=user_id, user_auth=user_auth)
        self._check_bound_user(user_id)
        _ = ledger_id
        payload = self._request(
            "POST",
            "/story/do",
            auth_required=True,
            json_body={"choice_id": str(choice_id), "payload": choice_payload},
        )
        return self._decode_runtime_envelope(payload)

    @service_method(
        access=ServiceAccess.CLIENT,
        context=ServiceContext.SESSION,
        writeback=ServiceWriteback.NONE,
        operation_id="story.update",
    )
    def get_story_update(
        self,
        *,
        user_id: UUID | None = None,
        ledger_id: UUID | None = None,
        user_auth: UserAuthInfo | None = None,
        since_step: int | None = None,
        limit: int = 0,
    ) -> RuntimeEnvelope:
        self._validate_user_auth(user_id=user_id, user_auth=user_auth)
        self._check_bound_user(user_id)
        _ = ledger_id
        params: dict[str, object] = {"limit": limit}
        if since_step is not None:
            params["since_step"] = since_step
        payload = self._request(
            "GET",
            "/story/update",
            auth_required=True,
            params=params,
        )
        return self._decode_runtime_envelope(payload)

    @service_method(
        access=ServiceAccess.CLIENT,
        context=ServiceContext.SESSION,
        writeback=ServiceWriteback.NONE,
        operation_id="story.info",
    )
    def get_story_info(
        self,
        *,
        user_id: UUID | None = None,
        ledger_id: UUID | None = None,
        user_auth: UserAuthInfo | None = None,
    ) -> ProjectedState:
        self._validate_user_auth(user_id=user_id, user_auth=user_auth)
        self._check_bound_user(user_id)
        _ = ledger_id
        payload = self._request("GET", "/story/info", auth_required=True)
        return self._decode_model(ProjectedState, payload, label="projected state")

    @service_method(
        access=ServiceAccess.CLIENT,
        context=ServiceContext.SESSION,
        writeback=ServiceWriteback.EXPLICIT,
        operation_id="story.drop",
    )
    def drop_story(
        self,
        *,
        user_id: UUID | None = None,
        ledger_id: UUID | None = None,
        user_auth: UserAuthInfo | None = None,
        archive: bool = False,
    ) -> RuntimeInfo:
        self._validate_user_auth(user_id=user_id, user_auth=user_auth)
        self._check_bound_user(user_id)
        _ = ledger_id
        payload = self._request(
            "DELETE",
            "/story/drop",
            auth_required=True,
            params={"archive": archive},
        )
        return self._decode_runtime_info(payload)

    @service_method(
        access=ServiceAccess.PUBLIC,
        context=ServiceContext.NONE,
        writeback=ServiceWriteback.EXPLICIT,
        operation_id="user.create",
    )
    def create_user(self, *, secret: str | None = None, **kwargs: Any) -> RuntimeInfo:
        self._reject_unexpected_kwargs("create_user", kwargs, allowed=set())
        next_secret = self._require_non_empty_secret(secret, method_name="create_user")
        payload = self._request(
            "POST",
            "/user/create",
            auth_required=False,
            params={"secret": next_secret},
        )
        secret_info = self._decode_model(UserSecret, payload, label="user secret")
        self._bind_auth_from_secret(secret_info)

        if secret_info.user_id is None:
            raise ServiceError("Remote service create_user did not return a user id")

        return RuntimeInfo.ok(
            message="User created",
            user_id=str(secret_info.user_id),
        )

    @service_method(
        access=ServiceAccess.CLIENT,
        context=ServiceContext.USER,
        writeback=ServiceWriteback.USER,
        operation_id="user.update",
    )
    def update_user(
        self,
        *,
        user_id: UUID,
        user_auth: UserAuthInfo | None = None,
        **kwargs: Any,
    ) -> RuntimeInfo:
        self._validate_user_auth(user_id=user_id, user_auth=user_auth)
        self._check_bound_user(user_id)
        self._reject_unexpected_kwargs("update_user", kwargs, allowed={"secret"})

        next_secret = self._require_non_empty_secret(
            kwargs.get("secret"),
            method_name="update_user",
        )
        payload = self._request(
            "PUT",
            "/user/secret",
            auth_required=True,
            params={"secret": next_secret},
        )
        secret_info = self._decode_model(UserSecret, payload, label="user secret")
        self._bind_auth_from_secret(secret_info)

        if secret_info.user_id is None:
            raise ServiceError("Remote service update_user did not return a user id")

        return RuntimeInfo.ok(
            message="User updated",
            user_id=str(secret_info.user_id),
            api_key=secret_info.api_key,
        )

    @service_method(
        access=ServiceAccess.CLIENT,
        context=ServiceContext.USER,
        writeback=ServiceWriteback.NONE,
        operation_id="user.info",
    )
    def get_user_info(
        self,
        *,
        user_id: UUID,
        user_auth: UserAuthInfo | None = None,
        **kwargs: Any,
    ) -> UserInfo:
        self._validate_user_auth(user_id=user_id, user_auth=user_auth)
        self._check_bound_user(user_id)
        self._reject_unexpected_kwargs("get_user_info", kwargs, allowed=set())
        payload = self._request("GET", "/user/info", auth_required=True)
        info = self._decode_model(UserInfo, payload, label="user info")
        self._bound_user_id = info.user_id
        return info

    @service_method(
        access=ServiceAccess.CLIENT,
        context=ServiceContext.USER,
        writeback=ServiceWriteback.EXPLICIT,
        operation_id="user.drop",
    )
    def drop_user(
        self,
        *,
        user_id: UUID,
        user_auth: UserAuthInfo | None = None,
    ) -> RuntimeInfo:
        self._validate_user_auth(user_id=user_id, user_auth=user_auth)
        self._check_bound_user(user_id)
        payload = self._request("DELETE", "/user/drop", auth_required=True)
        return self._decode_runtime_info(payload)

    @service_method(
        access=ServiceAccess.PUBLIC,
        context=ServiceContext.NONE,
        writeback=ServiceWriteback.NONE,
        operation_id="user.key",
    )
    def get_key_for_secret(self, *, secret: str) -> UserSecret:
        payload = self._request(
            "GET",
            "/system/secret",
            auth_required=False,
            params={"secret": secret},
        )
        return self._decode_model(UserSecret, payload, label="user secret")

    @service_method(
        access=ServiceAccess.PUBLIC,
        context=ServiceContext.NONE,
        writeback=ServiceWriteback.NONE,
        operation_id="world.list",
    )
    def list_worlds(self) -> list[WorldInfo]:
        payload = self._request("GET", "/system/worlds", auth_required=False)
        if not isinstance(payload, list):
            raise ServiceError("Remote service returned invalid world list payload")
        return [
            self._decode_model(WorldInfo, item, label="world info")
            for item in payload
        ]

    @service_method(
        access=ServiceAccess.PUBLIC,
        context=ServiceContext.WORLD,
        writeback=ServiceWriteback.NONE,
        operation_id="world.info",
    )
    def get_world_info(self, *, world_id: str) -> WorldInfo:
        payload = self._request(
            "GET",
            f"/world/{world_id}/info",
            auth_required=False,
        )
        return self._decode_model(WorldInfo, payload, label="world info")

    @service_method(
        access=ServiceAccess.PUBLIC,
        context=ServiceContext.WORLD,
        writeback=ServiceWriteback.NONE,
        capability="media",
        operation_id="world.media",
    )
    def get_world_media(
        self,
        *,
        world_id: str,
        media: MediaRIT | Identifier,
        **kwargs: Any,
    ) -> object:
        _ = (world_id, media, kwargs)
        raise self._unsupported("get_world_media")

    @service_method(
        access=ServiceAccess.DEV,
        context=ServiceContext.NONE,
        writeback=ServiceWriteback.EXPLICIT,
        blocking=BlockingMode.MAY_BLOCK,
        capability="world_mutation",
        operation_id="world.load",
    )
    def load_world(
        self,
        *,
        script_path: str | Path | None = None,
        script_data: UnstructuredData = None,
    ) -> RuntimeInfo:
        _ = (script_path, script_data)
        raise self._unsupported("load_world")

    @service_method(
        access=ServiceAccess.DEV,
        context=ServiceContext.WORLD,
        writeback=ServiceWriteback.EXPLICIT,
        capability="world_mutation",
        operation_id="world.unload",
    )
    def unload_world(self, *, world_id: str) -> RuntimeInfo:
        _ = world_id
        raise self._unsupported("unload_world")

    @service_method(
        access=ServiceAccess.PUBLIC,
        context=ServiceContext.NONE,
        writeback=ServiceWriteback.NONE,
        operation_id="system.info",
    )
    def get_system_info(self) -> SystemInfo:
        payload = self._request("GET", "/system/info", auth_required=False)
        return self._decode_model(SystemInfo, payload, label="system info")

    @service_method(
        access=ServiceAccess.DEV,
        context=ServiceContext.NONE,
        writeback=ServiceWriteback.NONE,
        capability="dev_tools",
        operation_id="system.reset",
    )
    def reset_system(self, *, hard: bool = False) -> RuntimeInfo:
        _ = hard
        raise self._unsupported("reset_system")


__all__ = ["RemoteServiceManager"]
