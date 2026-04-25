"""Canonical explicit service-manager API for StoryTangl."""

from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, TYPE_CHECKING
from uuid import UUID

import yaml

from tangl.core import BaseFragment
from tangl.persistence import PersistenceManager
from tangl.story import InitMode, World
from tangl.type_hints import Identifier, UnstructuredData
from tangl.utils.hash_secret import key_for_secret
from tangl.vm.runtime.ledger import Ledger

from .exceptions import AuthMismatchError
from ._user_support import parse_bool_flag, parse_datetime_field
from .diagnostics import diagnostics_from_codec_state, diagnostics_from_compile_issues
from .media import resolve_world_media
from .response import (
    PreflightReport,
    ProjectedState,
    RuntimeEnvelope,
    RuntimeInfo,
    SystemInfo,
    UserInfo,
    UserSecret,
    WorldInfo,
)
from .service_method import (
    BlockingMode,
    ServiceAccess,
    ServiceContext,
    ServiceMethodSpec,
    ServiceWriteback,
    get_service_method_spec,
    service_method,
)
from .system_info import get_system_info, reset_system
from .story_info import resolve_story_info_projector
from .user import User
from .world_registry import (
    WorldRegistry,
    iter_manual_worlds,
    legacy_world_label,
    pop_manual_world,
    register_manual_world,
    resolve_world,
)

if TYPE_CHECKING:  # pragma: no cover
    from tangl.media import MediaDataType
    from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
    from .auth import UserAuthInfo


@dataclass
class ServiceSession:
    """Live user/ledger/frame bundle opened by :class:`ServiceManager`."""

    user: User | None
    ledger: Ledger
    frame: Any


class ServiceManager:
    """Explicit public service API over persistence-backed story resources."""

    def __init__(self, persistence_manager: PersistenceManager | None = None) -> None:
        self.persistence = persistence_manager

    @classmethod
    def get_service_methods(cls) -> "OrderedDict[str, ServiceMethodSpec]":
        """Return canonical public service-method metadata in declaration order."""

        methods: "OrderedDict[str, ServiceMethodSpec]" = OrderedDict()
        for base in reversed(cls.__mro__):
            for name, value in base.__dict__.items():
                spec = get_service_method_spec(value)
                if spec is None:
                    continue
                methods[name] = spec.with_name(name)
        return methods

    def _validate_user_auth(
        self,
        *,
        user_id: UUID | None = None,
        user_auth: "UserAuthInfo | None" = None,
    ) -> None:
        if user_auth is None or user_id is None:
            return
        if user_auth.user_id != user_id:
            raise AuthMismatchError(
                f"user_id {user_id} does not match authenticated user {user_auth.user_id}",
            )

    def _require_persistence(self) -> PersistenceManager:
        if self.persistence is None:
            raise RuntimeError("Persistence manager required for resource access")
        return self.persistence

    def _load_user(self, user_id: UUID) -> User:
        persistence = self._require_persistence()
        if user_id not in persistence:
            raise ValueError(f"User {user_id} not found")
        user = persistence.load(user_id)
        if not isinstance(user, User):
            raise TypeError(f"Expected User for {user_id}, got {type(user).__name__}")
        return user

    def _load_ledger(self, ledger_id: UUID) -> Ledger:
        persistence = self._require_persistence()
        if ledger_id not in persistence:
            raise ValueError(f"Ledger {ledger_id} not found")
        ledger = persistence.load(ledger_id)
        if not isinstance(ledger, Ledger):
            raise TypeError(f"Expected Ledger for {ledger_id}, got {type(ledger).__name__}")
        return ledger

    def _save(self, payload: Any) -> None:
        persistence = self._require_persistence()
        persistence.save(payload)

    def _delete(self, uid: UUID) -> bool:
        if self.persistence is None:
            return False
        try:
            self.persistence.remove(uid)
            return True
        except KeyError:
            return False

    @contextmanager
    def open_user(
        self,
        user_id: UUID,
        *,
        write_back: bool = False,
    ) -> Iterator[User]:
        """Open one persisted user resource."""

        persistence = self._require_persistence()
        if user_id not in persistence:
            raise ValueError(f"User {user_id} not found")
        with persistence.open(user_id, write_back=write_back) as user:
            if not isinstance(user, User):
                raise TypeError(f"Expected User for {user_id}, got {type(user).__name__}")
            yield user

    @contextmanager
    def open_ledger(
        self,
        ledger_id: UUID,
        *,
        write_back: bool = False,
    ) -> Iterator[Ledger]:
        """Open one persisted ledger resource."""

        persistence = self._require_persistence()
        if ledger_id not in persistence:
            raise ValueError(f"Ledger {ledger_id} not found")
        with persistence.open(ledger_id, write_back=write_back) as ledger:
            if not isinstance(ledger, Ledger):
                raise TypeError(f"Expected Ledger for {ledger_id}, got {type(ledger).__name__}")
            yield ledger

    def open_world(self, world_id: str, /) -> World:
        """Resolve one world by id."""

        world = resolve_world(world_id)
        if not isinstance(world, World):
            raise TypeError(f"Expected Story world for '{world_id}', got {type(world).__name__}")
        return world

    @contextmanager
    def open_session(
        self,
        *,
        user_id: UUID | None = None,
        ledger_id: UUID | None = None,
        write_back: bool = False,
        user_auth: "UserAuthInfo | None" = None,
    ) -> Iterator[ServiceSession]:
        """Open a linked user/ledger session context."""

        self._validate_user_auth(user_id=user_id, user_auth=user_auth)

        if user_id is not None:
            with self.open_user(user_id, write_back=write_back) as user:
                effective_ledger_id = ledger_id or user.current_ledger_id
                if effective_ledger_id is None:
                    raise ValueError("User has no active ledger")
                with self.open_ledger(effective_ledger_id, write_back=write_back) as ledger:
                    ledger.user = user
                    ledger.user_id = user.uid
                    yield ServiceSession(user=user, ledger=ledger, frame=ledger.get_frame())
                return

        if ledger_id is None:
            raise ValueError("user_id or ledger_id is required to open a session")

        with self.open_ledger(ledger_id, write_back=write_back) as ledger:
            effective_user_id = ledger.user_id
            if effective_user_id is None:
                yield ServiceSession(user=None, ledger=ledger, frame=ledger.get_frame())
                return

            if user_auth is not None and user_auth.user_id != effective_user_id:
                raise AuthMismatchError(
                    f"user_id {effective_user_id} does not match authenticated user {user_auth.user_id}",
                )

            with self.open_user(effective_user_id, write_back=write_back) as user:
                ledger.user = user
                ledger.user_id = user.uid
                yield ServiceSession(user=user, ledger=ledger, frame=ledger.get_frame())

    @staticmethod
    def _resolve_world_id(ledger: Ledger) -> str | None:
        world = getattr(getattr(ledger, "graph", None), "world", None)
        if world is None:
            return None
        for attr in ("label", "uid"):
            value = getattr(world, attr, None)
            if value is not None:
                return str(value)
        return None

    @staticmethod
    def _build_runtime_envelope(
        ledger: Ledger,
        *,
        fragments: list[BaseFragment],
        metadata: dict[str, Any] | None = None,
    ) -> RuntimeEnvelope:
        merged_metadata = dict(metadata or {})
        world_id = ServiceManager._resolve_world_id(ledger)
        if world_id is not None:
            merged_metadata.setdefault("world_id", world_id)
        merged_metadata.setdefault("ledger_id", str(ledger.uid))
        return RuntimeEnvelope(
            cursor_id=ledger.cursor_id,
            step=ledger.step,
            fragments=list(fragments),
            last_redirect=ledger.last_redirect,
            redirect_trace=list(ledger.redirect_trace),
            metadata=merged_metadata,
        )

    @staticmethod
    def _prime_initial_update(ledger: Ledger) -> None:
        """Seed entry JOURNAL output for a freshly created ledger."""

        if ledger.get_journal():
            return

        frame = ledger.get_frame()
        frame.goto_node(ledger.cursor)

        prev_id = ledger.cursor_history[-1] if ledger.cursor_history else None
        for node_id in frame.cursor_trace:
            if prev_id is not None and node_id == prev_id:
                ledger.reentrant_steps += 1
            prev_id = node_id

        ledger.cursor_steps += frame.cursor_steps
        ledger.cursor_id = frame.cursor.uid
        ledger.cursor_history.extend(frame.cursor_trace)
        ledger.call_stack_ids = [edge.uid for edge in frame.return_stack]
        ledger.last_redirect = frame.last_redirect
        ledger.redirect_trace = list(frame.redirect_trace)
        ledger.save_snapshot(cadence=ledger.checkpoint_cadence)

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
        user_auth: "UserAuthInfo | None" = None,
        **kwargs: Any,
    ) -> RuntimeEnvelope:
        """Create a story session and return the initial runtime envelope."""

        self._validate_user_auth(user_id=user_id, user_auth=user_auth)

        import tangl.story  # noqa: F401  # ensure story-level hooks are registered

        with self.open_user(user_id, write_back=True) as user:
            world = kwargs.pop("world", None) or self.open_world(world_id)
            story_label = kwargs.get("story_label") or f"story_{user.uid}"
            mode_raw = kwargs.get("init_mode") or kwargs.get("mode") or InitMode.EAGER.value
            mode = InitMode(mode_raw.lower()) if isinstance(mode_raw, str) else InitMode(mode_raw)
            freeze_shape = bool(kwargs.get("freeze_shape", False))
            worker_dispatcher = kwargs.get("worker_dispatcher")
            namespace = dict(kwargs.pop("namespace", None) or {})
            namespace.setdefault("user", user)

            init_result = world.create_story(
                story_label,
                init_mode=mode,
                freeze_shape=freeze_shape,
                namespace=namespace,
            )
            story_graph = init_result.graph
            if story_graph.initial_cursor_id is None:
                raise RuntimeError("Story graph did not define an initial cursor")

            ledger = Ledger.from_graph(
                graph=story_graph,
                entry_id=story_graph.initial_cursor_id,
                uid=story_graph.story_id or story_graph.uid,
            )
            ledger.user = user
            ledger.user_id = user.uid
            ledger.worker_dispatcher = worker_dispatcher
            self._prime_initial_update(ledger)
            user.current_ledger_id = ledger.uid
            self._save(ledger)

            return self._build_runtime_envelope(
                ledger,
                fragments=list(ledger.get_journal()),
                metadata={"world_id": world_id},
            )

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
        user_auth: "UserAuthInfo | None" = None,
        choice_payload: Any = None,
    ) -> RuntimeEnvelope:
        """Resolve one choice edge and return the newest runtime envelope."""

        with self.open_session(
            user_id=user_id,
            ledger_id=ledger_id,
            write_back=True,
            user_auth=user_auth,
        ) as session:
            before_step = session.ledger.step
            session.ledger.resolve_choice(choice_id, choice_payload=choice_payload)
            fragments = list(session.ledger.get_journal(since_step=max(before_step + 1, 0)))
            return self._build_runtime_envelope(session.ledger, fragments=fragments)

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
        user_auth: "UserAuthInfo | None" = None,
        since_step: int | None = None,
        limit: int = 0,
    ) -> RuntimeEnvelope:
        """Return ordered runtime fragments for the active story session."""

        with self.open_session(
            user_id=user_id,
            ledger_id=ledger_id,
            write_back=False,
            user_auth=user_auth,
        ) as session:
            effective_since = 0 if since_step is None else since_step
            fragments = list(session.ledger.get_journal(since_step=effective_since, limit=limit))
            return self._build_runtime_envelope(session.ledger, fragments=fragments)

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
        user_auth: "UserAuthInfo | None" = None,
    ) -> ProjectedState:
        """Return projected current-state sections for the active story."""

        with self.open_session(
            user_id=user_id,
            ledger_id=ledger_id,
            write_back=False,
            user_auth=user_auth,
        ) as session:
            projector = resolve_story_info_projector(session.ledger)
            return projector.project(ledger=session.ledger)

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
        user_auth: "UserAuthInfo | None" = None,
        archive: bool = False,
    ) -> RuntimeInfo:
        """Clear the active story and optionally delete the persisted ledger."""

        with self.open_session(
            user_id=user_id,
            ledger_id=ledger_id,
            write_back=False,
            user_auth=user_auth,
        ) as session:
            if session.user is None:
                raise ValueError("Story drop requires a user-bound session")

            current_ledger_id = session.user.current_ledger_id or session.ledger.uid
            session.user.current_ledger_id = None
            self._save(session.user)

            details: dict[str, Any] = {
                "dropped_ledger_id": str(current_ledger_id),
                "archived": archive,
            }
            if not archive:
                from tangl.media.story_media import remove_story_media

                details["story_media_deleted"] = remove_story_media(current_ledger_id)
                details["persistence_deleted"] = self._delete(current_ledger_id)

            return RuntimeInfo.ok(
                cursor_id=session.ledger.cursor_id,
                step=session.ledger.step,
                message="Story dropped",
                **details,
            )

    @service_method(
        access=ServiceAccess.PUBLIC,
        context=ServiceContext.NONE,
        writeback=ServiceWriteback.EXPLICIT,
        operation_id="user.create",
    )
    def create_user(self, *, secret: str | None = None, **kwargs: Any) -> RuntimeInfo:
        """Create and persist a service user."""

        user = User(**kwargs)
        if isinstance(secret, str) and secret:
            user.set_secret(secret)
        self._save(user)
        return RuntimeInfo.ok(
            message="User created",
            user_id=str(user.uid),
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
        user_auth: "UserAuthInfo | None" = None,
        **kwargs: Any,
    ) -> RuntimeInfo:
        """Update one persisted user record."""

        self._validate_user_auth(user_id=user_id, user_auth=user_auth)
        with self.open_user(user_id, write_back=True) as user:
            secret = kwargs.pop("secret", None)
            api_key: str | None = None
            if isinstance(secret, str) and secret:
                user.set_secret(secret)
                api_key = key_for_secret(secret)

            if "last_played_dt" in kwargs:
                user.last_played_dt = parse_datetime_field(
                    kwargs["last_played_dt"],
                    field_name="last_played_dt",
                )
            if "privileged" in kwargs:
                next_privileged = parse_bool_flag(
                    kwargs["privileged"],
                    field_name="privileged",
                )
                if bool(getattr(user, "privileged", False)):
                    user.privileged = next_privileged

            details: dict[str, Any] = {"user_id": str(user.uid)}
            if api_key is not None:
                details["api_key"] = api_key
            return RuntimeInfo.ok(message="User updated", **details)

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
        user_auth: "UserAuthInfo | None" = None,
        **kwargs: Any,
    ) -> UserInfo:
        """Return persisted user profile information."""

        self._validate_user_auth(user_id=user_id, user_auth=user_auth)
        with self.open_user(user_id, write_back=False) as user:
            return UserInfo.from_user(user, **kwargs)

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
        user_auth: "UserAuthInfo | None" = None,
    ) -> RuntimeInfo:
        """Delete one persisted user record."""

        self._validate_user_auth(user_id=user_id, user_auth=user_auth)
        with self.open_user(user_id, write_back=False) as user:
            dropped_ledger_id = user.current_ledger_id

        deleted = self._delete(user_id)
        details: dict[str, Any] = {
            "user_id": str(user_id),
            "persistence_deleted": deleted,
        }
        if dropped_ledger_id is not None:
            details["dropped_ledger_id"] = str(dropped_ledger_id)
        return RuntimeInfo.ok(message="User dropped", **details)

    @service_method(
        access=ServiceAccess.PUBLIC,
        context=ServiceContext.NONE,
        writeback=ServiceWriteback.NONE,
        operation_id="user.key",
    )
    def get_key_for_secret(self, *, secret: str) -> UserSecret:
        """Encode a user secret as an API key."""

        return UserSecret(api_key=key_for_secret(secret), user_secret=secret)

    @service_method(
        access=ServiceAccess.PUBLIC,
        context=ServiceContext.NONE,
        writeback=ServiceWriteback.NONE,
        operation_id="world.list",
    )
    def list_worlds(self) -> list[WorldInfo]:
        """List available worlds as typed info models."""

        registry = WorldRegistry()
        worlds = registry.list_worlds()

        manual_worlds = dict(iter_manual_worlds())
        if manual_worlds:
            known = {item.get("label") for item in worlds}
            for label, world in manual_worlds.items():
                if label in known:
                    continue
                worlds.append(
                    {
                        "label": label,
                        "metadata": world.metadata or {},
                        "is_anthology": False,
                    },
                )

        info_models: list[WorldInfo] = []
        for world in worlds:
            metadata = dict(world.get("metadata") or {})
            info_models.append(
                WorldInfo(
                    label=world["label"],
                    title=str(metadata.get("title", world["label"])),
                    author=metadata.get("author") or "Unknown",
                ),
            )
        return info_models

    @service_method(
        access=ServiceAccess.PUBLIC,
        context=ServiceContext.WORLD,
        writeback=ServiceWriteback.NONE,
        operation_id="world.info",
    )
    def get_world_info(self, *, world_id: str) -> WorldInfo:
        """Return metadata for one resolved world."""

        world = self.open_world(world_id)
        metadata = dict(world.metadata or {})
        metadata.pop("label", None)
        metadata.setdefault("title", world.label)
        metadata.setdefault("author", "Unknown")
        return WorldInfo(label=world.label, **metadata)

    @service_method(
        access=ServiceAccess.PUBLIC,
        context=ServiceContext.WORLD,
        writeback=ServiceWriteback.NONE,
        operation_id="world.preflight",
    )
    def preflight_world(self, *, world_id: str) -> PreflightReport:
        """Compile one discovered world bundle and return authoring diagnostics."""

        registry = WorldRegistry()
        bundle = registry.bundles.get(world_id)
        if bundle is None:
            if world_id in dict(iter_manual_worlds()):
                return PreflightReport(
                    world_id=world_id,
                    status="ok",
                    diagnostics=[],
                )
            raise ValueError(f"Unknown world: {world_id}")

        world = registry.compiler.compile(bundle)
        diagnostics = [
            *diagnostics_from_codec_state(world.bundle.codec_state),
            *diagnostics_from_compile_issues(world.bundle.issues),
        ]
        status = "error" if any(item.severity == "error" for item in diagnostics) else "ok"
        return PreflightReport(
            world_id=world_id,
            status=status,
            diagnostics=diagnostics,
        )

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
        media: "MediaRIT | Identifier",
        **kwargs: Any,
    ) -> Any:
        """Return implementation-specific media content for one world asset."""

        return resolve_world_media(
            world=self.open_world(world_id),
            media=media,
            **kwargs,
        )

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
        """Load one ad hoc world into the process-local manual registry."""

        if script_path is not None:
            path = Path(script_path)
            if not path.exists():
                raise FileNotFoundError(f"Script not found: {script_path}")
            script_data = yaml.safe_load(path.read_text(encoding="utf-8"))

        if not isinstance(script_data, dict):
            raise ValueError("script_data is required to load a world")

        legacy_label = legacy_world_label(script_data)
        world = World.from_script_data(
            script_data=script_data,
            label=legacy_label,
        )
        register_manual_world(world)
        return RuntimeInfo.ok(message="World loaded", world_label=world.label)

    @service_method(
        access=ServiceAccess.DEV,
        context=ServiceContext.WORLD,
        writeback=ServiceWriteback.EXPLICIT,
        capability="world_mutation",
        operation_id="world.unload",
    )
    def unload_world(self, *, world_id: str) -> RuntimeInfo:
        """Unload one process-local manual world."""

        world = self.open_world(world_id)
        removed = pop_manual_world(world.label)
        if removed is None:
            return RuntimeInfo.error(
                code="WORLD_NOT_MANUAL",
                message="No manual world to unload",
                world_label=world.label,
            )
        return RuntimeInfo.ok(message="World unloaded", world_label=world.label)

    @service_method(
        access=ServiceAccess.PUBLIC,
        context=ServiceContext.NONE,
        writeback=ServiceWriteback.NONE,
        operation_id="system.info",
    )
    def get_system_info(self) -> SystemInfo:
        """Return service/system metadata."""

        return get_system_info()

    @service_method(
        access=ServiceAccess.DEV,
        context=ServiceContext.NONE,
        writeback=ServiceWriteback.NONE,
        capability="dev_tools",
        operation_id="system.reset",
    )
    def reset_system(self, *, hard: bool = False) -> RuntimeInfo:
        """Implementation-specific system reset hook."""

        return reset_system(hard=hard)


__all__ = [
    "ServiceManager",
    "ServiceSession",
]
