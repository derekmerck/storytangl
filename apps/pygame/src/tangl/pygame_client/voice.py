"""Serial, occurrence-deduplicated barks for one immediate presentation batch."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
import logging
from uuid import UUID

import pygame

from tangl.journal.fragments import MediaFragment
from tangl.service.response import JsonValue

from .music import MusicPlayer

logger = logging.getLogger(__name__)


class VoicePlayer:
    """Play fresh barks without blocking prose or owning narrative timing."""

    def __init__(self, music: MusicPlayer) -> None:
        self.music = music
        self.current: MediaFragment | None = None
        self._pending: deque[tuple[MediaFragment, dict[str, JsonValue] | None]] = deque()
        self._seen: set[UUID] = set()
        self._channel: pygame.mixer.Channel | None = None
        self._end_event = pygame.event.custom_type()

    def present(
        self, cues: Sequence[tuple[MediaFragment, dict[str, JsonValue] | None]],
        *, fresh: bool,
    ) -> None:
        unseen = []
        for cue, payload in cues:
            if cue.uid not in self._seen:
                self._seen.add(cue.uid)
                unseen.append((cue, payload))
        if not fresh:
            return
        # Duplicate delivery is not another presentation. Empty fresh output,
        # however, advances prose and must cancel unfinished old dialogue.
        if cues and not unseen:
            return
        self.cancel()
        self._pending.extend(unseen)
        self._advance()

    def _advance(self) -> None:
        self.current = None
        while self._pending:
            cue, payload = self._pending.popleft()
            if (
                payload is None or payload.get("fragment_type") != "media"
                or payload.get("media_type") != "audio"
                or payload.get("content_format") != "path"
                or not isinstance(payload.get("path"), str)
            ):
                logger.warning("Bark unavailable: requires co-located audio (%s)", cue.uid)
                continue
            if not self.music.ensure_device():
                logger.warning("Bark unavailable: audio device (%s)", cue.uid)
                continue
            try:
                sound = pygame.mixer.Sound(payload["path"])
                # Channel zero is dedicated to voice; music uses mixer.music.
                pygame.mixer.set_reserved(1)
                self._channel = pygame.mixer.Channel(0)
                self._channel.set_endevent(self._end_event)
                self._channel.play(sound)
                self.current = cue
                self.music.set_ducked(True)
                return
            except (pygame.error, OSError) as error:
                logger.warning("Bark unavailable (%s): %s", cue.uid, error)
        self.music.set_ducked(False)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type != self._end_event:
            return False
        # stop() can leave an old event in an already-drained event batch.
        # Such an event cannot interrupt a newer clip. If that clip has itself
        # finished, advancing is safe; its later event sees the next clip busy.
        if self.current is not None:
            try:
                if not self._channel.get_busy():
                    self._advance()
            except pygame.error as error:
                logger.warning("Bark channel unavailable: %s", error)
                self.cancel()
        return True

    def cancel(self) -> None:
        self._pending.clear()
        self.current = None
        if self._channel is not None:
            try:
                self._channel.set_endevent()
                self._channel.stop()
            except pygame.error as error:
                logger.warning("Bark channel unavailable: %s", error)
            self._channel = None
        self.music.set_ducked(False)

    def close(self) -> None:
        self.cancel()
        self._seen.clear()
