from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any
from uuid import UUID

from tangl.core import BaseFragment
from tangl.journal.fragments import (
    AttributedFragment,
    BlockFragment,
    ChoiceFragment,
    ContentFragment,
    DialogFragment,
    MediaFragment,
)
from tangl.media.media_resource import MediaResourceInventoryTag as MediaRIT
from tangl.persistence import PersistenceManagerFactory
from tangl.service.media import (
    MediaContentProfile,
    MediaPendingPolicy,
    MediaRenderProfile,
    media_fragment_to_payload,
)
from tangl.service.response import RuntimeEnvelope, RuntimeInfo
from tangl.service.service_manager import ServiceManager
from tangl.utils.sanitize_str import sanitize_str

from .models import RenPyChoice, RenPyLine, RenPyMediaOp, RenPyTurn

logger = logging.getLogger(__name__)

_RIT_LABEL_RE = re.compile(r"label='([^']+)'")
_RIT_PATH_RE = re.compile(r"path=PosixPath\('([^']+)'\)")


def _non_empty_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _fragment_step(fragment: BaseFragment) -> int:
    raw_step = getattr(fragment, "step", 0)
    if raw_step is None:
        return 0
    try:
        step = int(raw_step)
    except (TypeError, ValueError):
        return 0
    return max(step, 0)


def _uuid_or_none(value: Any) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _speaker_tag(fragment: AttributedFragment) -> str:
    for attr in ("speaker_key", "speaker_label", "speaker_name", "who"):
        value = getattr(fragment, attr, None)
        if isinstance(value, str) and value.strip():
            return sanitize_str(value)
    return "speaker"


class RenPySessionBridge:
    """Thin manager-backed StoryTangl bridge for the Ren'Py demo app."""

    def __init__(
        self,
        service_manager: ServiceManager | None = None,
        *,
        user_id: UUID | None = None,
        user_secret: str | None = None,
        media_render_profile: MediaRenderProfile | None = None,
    ) -> None:
        self.service_manager = service_manager or ServiceManager(
            PersistenceManagerFactory.native_in_mem()
        )
        self.user_id = user_id
        self.user_secret = user_secret
        self.ledger_id: UUID | None = None
        self.world_id: str | None = None
        self.media_render_profile = media_render_profile or MediaRenderProfile(
            pending_policy=MediaPendingPolicy.FALLBACK,
            content_profile=MediaContentProfile.PASSTHROUGH,
        )

    def start(self, world_id: str) -> RuntimeEnvelope:
        """Create a fresh story session for ``world_id``."""

        user_id = self._ensure_user_id()
        self.world_id = world_id
        envelope = self.service_manager.create_story(
            user_id=user_id,
            world_id=world_id,
        )
        self._sync_ledger_id(envelope)
        return envelope

    def choose(
        self,
        choice_id: UUID,
        choice_payload: Any | None = None,
    ) -> RuntimeEnvelope:
        """Resolve one adapted choice against the active ledger."""

        if self.user_id is None or self.ledger_id is None:
            raise RuntimeError("RenPySessionBridge.choose() requires an active story session.")

        envelope = self.service_manager.resolve_choice(
            user_id=self.user_id,
            ledger_id=self.ledger_id,
            choice_id=choice_id,
            choice_payload=choice_payload,
        )
        self._sync_ledger_id(envelope)
        return envelope

    def build_turns(self, fragments: list[BaseFragment]) -> list[RenPyTurn]:
        """Group typed fragments into Ren'Py-friendly turns."""

        turns_by_step: dict[int, RenPyTurn] = {}
        for fragment in self._iter_fragments(fragments):
            step = _fragment_step(fragment)
            turn = turns_by_step.setdefault(step, RenPyTurn(step=step))
            self._append_fragment(turn=turn, fragment=fragment)
        return list(turns_by_step.values())

    def _ensure_user_id(self) -> UUID:
        if self.user_id is not None:
            return self.user_id

        info = self.service_manager.create_user(secret=self.user_secret)
        if not isinstance(info, RuntimeInfo):
            raise TypeError(f"Expected RuntimeInfo from create_user(), got {type(info)!r}")

        details = dict(info.details or {})
        user_id = _uuid_or_none(details.get("user_id"))
        if user_id is None:
            raise RuntimeError("create_user() did not return a user_id detail.")
        self.user_id = user_id
        return user_id

    def _sync_ledger_id(self, envelope: RuntimeEnvelope) -> None:
        metadata = dict(envelope.metadata or {})
        ledger_id = _uuid_or_none(metadata.get("ledger_id"))
        if ledger_id is None:
            raise RuntimeError("RuntimeEnvelope metadata did not include ledger_id.")
        self.ledger_id = ledger_id

    def _iter_fragments(self, fragments: list[BaseFragment]) -> list[BaseFragment]:
        flattened: list[BaseFragment] = []
        for fragment in fragments:
            flattened.extend(self._flatten_fragment(fragment))
        return flattened

    def _flatten_fragment(self, fragment: BaseFragment) -> list[BaseFragment]:
        if isinstance(fragment, DialogFragment):
            return list(fragment.content)

        if isinstance(fragment, BlockFragment):
            flattened: list[BaseFragment] = []
            if isinstance(fragment.content, str) and fragment.content.strip():
                flattened.append(
                    ContentFragment(
                        content=fragment.content,
                        source_id=getattr(fragment, "source_id", None),
                        step=_fragment_step(fragment),
                    )
                )
            flattened.extend(fragment.choices)
            return flattened

        return [fragment]

    def _append_fragment(self, *, turn: RenPyTurn, fragment: BaseFragment) -> None:
        if isinstance(fragment, AttributedFragment):
            self._append_attributed_fragment(turn=turn, fragment=fragment)
            return

        if isinstance(fragment, MediaFragment):
            self._append_media_fragment(turn=turn, fragment=fragment)
            return

        if isinstance(fragment, ChoiceFragment):
            choice_id = _uuid_or_none(fragment.edge_id)
            if choice_id is None:
                logger.debug("Ignoring choice fragment without edge_id: %r", fragment)
                return

            turn.choices.append(
                RenPyChoice(
                    choice_id=choice_id,
                    text=_non_empty_text(fragment.text)
                    or _non_empty_text(getattr(fragment, "content", None))
                    or str(choice_id),
                    available=bool(
                        fragment.active if fragment.active is not None else fragment.available
                    ),
                    unavailable_reason=fragment.unavailable_reason,
                    accepts=(
                        dict(fragment.accepts)
                        if isinstance(fragment.accepts, dict)
                        else None
                    ),
                    ui_hints=(
                        dict(fragment.ui_hints)
                        if isinstance(fragment.ui_hints, dict)
                        else None
                    ),
                    choice_payload=fragment.activation_payload,
                )
            )
            return

        if isinstance(fragment, ContentFragment):
            text = _non_empty_text(fragment.content) or _non_empty_text(
                getattr(fragment, "text", None)
            )
            if text is not None:
                turn.lines.append(RenPyLine(text=text))
            return

        logger.debug("Ignoring unsupported Ren'Py fragment type: %s", type(fragment).__name__)

    def _append_attributed_fragment(
        self,
        *,
        turn: RenPyTurn,
        fragment: AttributedFragment,
    ) -> None:
        portrait_tag = _speaker_tag(fragment)
        media_payload = self._media_payload_dict(getattr(fragment, "media_payload", None))
        if media_payload is not None:
            self._append_media_payload(
                turn=turn,
                payload=media_payload,
                default_role=_non_empty_text(getattr(fragment, "media", None)),
                default_tag=portrait_tag,
            )

        text = _non_empty_text(fragment.content) or _non_empty_text(getattr(fragment, "text", None))
        if text is None:
            return

        style_name = None
        hints = getattr(fragment, "presentation_hints", None)
        if hints is not None:
            style_name = _non_empty_text(getattr(hints, "style_name", None))

        turn.lines.append(
            RenPyLine(
                text=text,
                speaker=_non_empty_text(fragment.who),
                speaker_key=portrait_tag,
                style_name=style_name,
                portrait_tag=portrait_tag,
            )
        )

    def _append_media_fragment(
        self,
        *,
        turn: RenPyTurn,
        fragment: MediaFragment,
    ) -> None:
        normalized_fragment = self._normalize_media_fragment(fragment)
        payload = media_fragment_to_payload(
            normalized_fragment,
            render_profile=self.media_render_profile,
            world_id=self.world_id,
        )
        if payload is None:
            fallback_text = _non_empty_text(getattr(fragment, "text", None))
            if fallback_text is not None:
                turn.lines.append(RenPyLine(text=fallback_text))
            return

        fragment_type = payload.get("fragment_type")
        if fragment_type == "content":
            text = _non_empty_text(payload.get("content")) or _non_empty_text(payload.get("text"))
            if text is not None:
                turn.lines.append(RenPyLine(text=text))
            return

        if fragment_type != "media":
            logger.debug("Ignoring non-media Ren'Py payload: %r", payload)
            return

        self._append_media_payload(
            turn=turn,
            payload=payload,
            default_role=_non_empty_text(normalized_fragment.media_role),
            fallback_text=_non_empty_text(payload.get("text"))
            or _non_empty_text(getattr(fragment, "text", None)),
        )

    def _normalize_media_fragment(self, fragment: MediaFragment) -> MediaFragment:
        if fragment.content_format != "rit" or isinstance(fragment.content, MediaRIT):
            return fragment
        if not isinstance(fragment.content, str):
            return fragment

        path_match = _RIT_PATH_RE.search(fragment.content)
        if path_match is None:
            logger.debug("Ignoring non-parsable stringified MediaRIT: %r", fragment.content)
            return fragment

        path = Path(path_match.group(1))
        label_match = _RIT_LABEL_RE.search(fragment.content)
        rit_kwargs: dict[str, Any] = {
            "path": path,
            "data_type": getattr(fragment, "content_type", None),
        }
        if label_match is not None:
            rit_kwargs["label"] = label_match.group(1)

        try:
            rit = MediaRIT(**rit_kwargs)
        except Exception:
            logger.debug("Failed to rebuild MediaRIT from fragment content: %r", fragment.content)
            return fragment

        return fragment.model_copy(update={"content": rit})

    def _append_media_payload(
        self,
        *,
        turn: RenPyTurn,
        payload: dict[str, Any],
        default_role: str | None = None,
        default_tag: str | None = None,
        fallback_text: str | None = None,
    ) -> None:
        role = (
            _non_empty_text(payload.get("media_role"))
            or _non_empty_text(payload.get("role"))
            or default_role
        )
        source = self._payload_source(payload)

        if role not in {"narrative_im", "dialog_im"}:
            if role is not None:
                logger.debug("Ignoring unsupported Ren'Py media role: %s", role)
            if fallback_text is not None:
                turn.lines.append(RenPyLine(text=fallback_text))
            return

        if source is None:
            logger.debug("Ignoring media payload without local source: %r", payload)
            if fallback_text is not None:
                turn.lines.append(RenPyLine(text=fallback_text))
            return

        action = "scene" if role == "narrative_im" else "show"
        tag = "tangl_background" if role == "narrative_im" else (default_tag or "dialog_im")
        alt_text = (
            _non_empty_text(payload.get("alt_text"))
            or _non_empty_text(payload.get("description"))
            or fallback_text
        )
        turn.media_ops.append(
            RenPyMediaOp(
                action=action,
                role=role,
                source=source,
                tag=tag,
                position=_non_empty_text(payload.get("position")),
                alt_text=alt_text,
                content_format=_non_empty_text(payload.get("content_format")),
                source_id=_uuid_or_none(payload.get("source_id")),
            )
        )

    @staticmethod
    def _payload_source(payload: dict[str, Any]) -> str | None:
        for key in ("path", "url", "src", "ref"):
            value = payload.get(key)
            if isinstance(value, Path):
                return str(value)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _media_payload_dict(value: Any) -> dict[str, Any] | None:
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            payload = model_dump(mode="python")
            return payload if isinstance(payload, dict) else None
        if isinstance(value, dict):
            return dict(value)
        return None
