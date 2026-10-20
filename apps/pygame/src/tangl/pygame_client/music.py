"""One client-local music stream, separate from drawing and journal history."""

from __future__ import annotations

from collections.abc import Sequence
import logging
from uuid import UUID

import pygame

from tangl.journal.fragments import ControlFragment, MediaFragment
from tangl.service.response import JsonValue, PresentationSnapshot

logger = logging.getLogger(__name__)


class MusicPlayer:
    """Synchronize desired music; only fresh live controls can request restart."""

    def __init__(self, *, volume: float = 0.5, muted: bool = False) -> None:
        self.volume = max(0.0, min(1.0, volume))
        self.muted = muted
        self.current: MediaFragment | None = None
        self.error: str | None = None
        self._playing_rit: UUID | None = None
        self._seen_controls: set[UUID] = set()
        self._device_failed = False
        self._duck_gain = 1.0

    def synchronize(
        self, snapshot: PresentationSnapshot | None, payload: dict[str, JsonValue] | None,
        controls: Sequence[ControlFragment] = (), *, live: bool = False,
    ) -> None:
        previous_rit = self._playing_rit
        if snapshot is not None:
            selected = snapshot.music
            self.current = selected if isinstance(selected, MediaFragment) else None
            if self.current is None or payload is None:
                self._stop()
                self.error = "Music unavailable for this delivery profile" if self.current else None
                if self.error:
                    logger.warning("%s", self.error)
            elif (
                payload.get("fragment_type") != "media"
                or payload.get("media_type") != "audio"
                or payload.get("content_format") != "path"
                or not isinstance(payload.get("path"), str)
                or payload.get("rit_id") is None
            ):
                self._stop()
                self.error = "Music requires co-located path delivery"
                logger.warning("%s", self.error)
            elif UUID(str(payload["rit_id"])) != self._playing_rit:
                self._stop()
                self._load(payload["path"], UUID(str(payload["rit_id"])))
        for control in controls:
            if control.uid in self._seen_controls:
                continue
            self._seen_controls.add(control.uid)
            if not live or self.current is None or not control.matches(self.current):
                continue
            # A supplied snapshot is final selection, not a replay queue. An old
            # delete preceding a new cue in the same batch cannot clear that cue.
            if control.fragment_type == "delete" and snapshot is None:
                self.current = None
                self._stop()
            elif (
                control.media_action == "restart" and control.media is not None
                and control.media.rit_id == self.current.rit_id
                and self._playing_rit is not None and self._playing_rit == previous_rit
            ):
                self._play()
        if self.current is None:
            self._device_failed = False
            self.error = None

    def ensure_device(self) -> bool:
        """Share device initialization and retry policy with the voice channel."""
        if self._device_failed and not pygame.mixer.get_init():
            return False
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error as error:
                self._device_failed = True
                self._failed(error)
                return False
        self._device_failed = False
        return True

    def _load(self, path: str, rit_id: UUID) -> None:
        if not self.ensure_device():
            return
        try:
            pygame.mixer.music.load(path)
            self._play()
            if self.error is None:
                self._playing_rit = rit_id
        except (pygame.error, OSError) as error:
            self._failed(error)

    def _play(self) -> None:
        timing = self.current.staging_hints.media_timing if self.current.staging_hints else None
        if not self._apply_gain():
            return
        try:
            pygame.mixer.music.play(loops=-1 if timing == "loop" else 0)
            self.error = None
        except pygame.error as error:
            self._failed(error)

    def _failed(self, error: pygame.error | OSError) -> None:
        self.error = str(error)
        self._playing_rit = None
        logger.warning("Music unavailable: %s", error)

    def _stop(self) -> None:
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
            except pygame.error as error:
                self._failed(error)
        self._playing_rit = None

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, volume))
        self._apply_gain()

    def set_ducked(self, ducked: bool) -> None:
        self._duck_gain = 0.25 if ducked else 1.0
        self._apply_gain()

    def _apply_gain(self) -> bool:
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.set_volume(0.0 if self.muted else self.volume * self._duck_gain)
                return True
            except pygame.error as error:
                self._failed(error)
        return False

    def toggle_mute(self) -> None:
        self.muted = not self.muted
        self.set_volume(self.volume)

    def close(self) -> None:
        """End a story/session without discarding local listening preferences."""
        self._stop()
        self.current = None
        self.error = None
        self._device_failed = False
        self._seen_controls.clear()
        self._duck_gain = 1.0

    @property
    def status(self) -> str:
        if self.error or self._device_failed:
            return "unavailable"
        return "muted" if self.muted else f"{self.volume:.0%}"
