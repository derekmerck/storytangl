"""Session bridge from StoryTangl's service surface to the pygame turn model.

Imports no pygame, so the whole adaptation layer is testable under ordinary
pytest. The renderer lives in :mod:`tangl.pygame_client.stage`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from tangl.core import BaseFragment
from tangl.journal.fragments import (
    AttributedFragment,
    ChoiceFragment,
    ContentFragment,
    GroupFragment,
    MediaFragment,
)
from tangl.persistence import PersistenceManagerFactory
from tangl.service.media import (
    MediaContentProfile,
    MediaPendingPolicy,
    MediaRenderProfile,
    media_fragment_to_payload,
)
from tangl.service.response import DirectEdgeRequest, RuntimeEnvelope, RuntimeInfo
from tangl.service.service_manager import ServiceManager

from .models import Choice, Line, StageImage, Turn

logger = logging.getLogger(__name__)


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip() or None


# Media payloads name their source by content_format. ``content``/``source`` are
# not among them; see ``tangl.service.media.media_fragment_to_payload``.
_SOURCE_KEYS = ("path", "url", "src", "ref")


def _payload_source(payload: dict[str, Any]) -> str | None:
    """Return the first usable media source key in a service payload."""

    for key in _SOURCE_KEYS:
        value = payload.get(key)
        if isinstance(value, Path):
            return str(value)
        if (text := _text(value)) is not None:
            return text
    return None


def _step(fragment: BaseFragment) -> int:
    try:
        return max(int(getattr(fragment, "step", 0) or 0), 0)
    except (TypeError, ValueError):
        return 0


class PygameSessionBridge:
    """Own the story session and adapt envelopes into :class:`Turn` values."""

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

    # ── session lifecycle ────────────────────────────────────────────────

    def start(self, world_id: str) -> RuntimeEnvelope:
        """Create a fresh story session for ``world_id``."""

        user_id = self._ensure_user_id()
        self.world_id = world_id
        envelope = self.service_manager.create_story(
            user_id=user_id,
            world_id=world_id,
        )
        self._sync(envelope)
        return envelope

    def choose(self, edge_id: UUID, payload: Any | None = None) -> RuntimeEnvelope:
        """Commit one choice by edge id."""

        if self.user_id is None or self.ledger_id is None:
            raise RuntimeError("choose() requires an active story session")
        envelope = self.service_manager.resolve_choice(
            user_id=self.user_id,
            ledger_id=self.ledger_id,
            request=DirectEdgeRequest(edge_id=edge_id, payload=payload),
        )
        self._sync(envelope)
        return envelope

    def _ensure_user_id(self) -> UUID:
        """Register a session user; the service will not accept an invented id."""

        if self.user_id is not None:
            return self.user_id
        info = self.service_manager.create_user(secret=self.user_secret)
        if not isinstance(info, RuntimeInfo):
            raise TypeError(f"Expected RuntimeInfo from create_user(), got {type(info)!r}")
        raw = dict(info.details or {}).get("user_id")
        if raw is None:
            raise RuntimeError("create_user() did not return a user_id detail")
        self.user_id = raw if isinstance(raw, UUID) else UUID(str(raw))
        return self.user_id

    def _sync(self, envelope: RuntimeEnvelope) -> None:
        """Track the active ledger, which travels in envelope metadata."""

        raw = dict(envelope.metadata or {}).get("ledger_id")
        if raw is None:
            raise RuntimeError("RuntimeEnvelope metadata did not include ledger_id")
        self.ledger_id = raw if isinstance(raw, UUID) else UUID(str(raw))

    # ── adaptation ───────────────────────────────────────────────────────

    def build_turns(self, fragments: list[BaseFragment]) -> list[Turn]:
        """Group fragments into per-step turns, in stream order."""

        turns: dict[int, Turn] = {}
        for fragment in self._flatten(fragments):
            step = _step(fragment)
            self._append(turns.setdefault(step, Turn(step=step)), fragment)
        return [turns[step] for step in sorted(turns)]

    def _flatten(self, fragments: list[BaseFragment]) -> list[BaseFragment]:
        flat: list[BaseFragment] = []
        for fragment in fragments:
            if isinstance(fragment, GroupFragment):
                flat.extend(self._flatten(list(getattr(fragment, "content", []) or [])))
                continue
            flat.append(fragment)
        return flat

    def _append(self, turn: Turn, fragment: BaseFragment) -> None:
        if isinstance(fragment, ChoiceFragment):
            turn.choices.append(
                Choice(
                    edge_id=fragment.edge_id,
                    text=_text(fragment.text) or "(unnamed choice)",
                    available=bool(getattr(fragment, "available", True)),
                    unavailable_reason=_text(getattr(fragment, "unavailable_reason", None)),
                    payload=fragment.activation_payload,
                )
            )
            return

        if isinstance(fragment, MediaFragment):
            self._append_media(turn, fragment)
            return

        # AttributedFragment subclasses ContentFragment, so it is checked first.
        if isinstance(fragment, AttributedFragment):
            text = _text(fragment.content)
            if text is not None:
                turn.lines.append(
                    Line(
                        text=text,
                        speaker=_text(fragment.who),
                        manner=_text(fragment.how),
                    )
                )
            return

        if isinstance(fragment, ContentFragment):
            text = _text(fragment.content)
            if text is not None:
                turn.lines.append(Line(text=text))

    @staticmethod
    def _append_fallback_text(
        turn: Turn,
        payload: dict[str, Any] | None,
        fragment: MediaFragment,
    ) -> None:
        """Render whatever text stands in for media that cannot be shown."""

        text = None
        if payload is not None:
            text = _text(payload.get("content")) or _text(payload.get("text"))
        if text is None:
            text = _text(getattr(fragment, "text", None))
        if text is not None:
            turn.lines.append(Line(text=text))

    def _append_media(self, turn: Turn, fragment: MediaFragment) -> None:
        payload = media_fragment_to_payload(
            fragment,
            render_profile=self.media_render_profile,
            world_id=self.world_id,
        )
        if payload is None or payload.get("fragment_type") != "media":
            # Media that cannot be dereferenced degrades to its text floor. The
            # service may supply that text itself, so prefer the payload's.
            self._append_fallback_text(turn, payload, fragment)
            return

        source = _payload_source(payload)
        if source is None:
            logger.debug("Media payload without a usable source: %r", payload)
            self._append_fallback_text(turn, payload, fragment)
            return
        hints = fragment.staging_hints
        turn.images.append(
            StageImage(
                role=_text(payload.get("media_role")) or _text(fragment.media_role) or "media",
                source=source,
                alt_text=_text(payload.get("text")),
                source_id=getattr(fragment, "rit_id", None),
                flip_h=bool(getattr(hints, "media_flip_h", None)),
            )
        )
