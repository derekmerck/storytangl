"""Read-only projection of canonical journal intent, not playback state."""

from __future__ import annotations

from collections.abc import Iterable

from tangl.core import BaseFragment
from tangl.presentation.hints import StagingHints

from .fragments import ControlFragment, MediaFragment


def desired_music(fragments: Iterable[BaseFragment]) -> MediaFragment | None:
    """Fold history before slicing or capability/transport projection.

    Restating a RIT does not imply restart. Restart controls are live events,
    not changes to desired selection or repetition, and are absent in snapshots.
    """
    music: MediaFragment | None = None
    for fragment in fragments:
        if isinstance(fragment, MediaFragment):
            if fragment.media_role == "music" and fragment.rit_id is not None:
                if (
                    music is not None
                    and fragment.rit_id == music.rit_id
                    and music.staging_hints is not None
                    and (
                        fragment.staging_hints is None
                        or fragment.staging_hints.media_timing is None
                    )
                ):
                    hints = fragment.staging_hints or StagingHints()
                    fragment = fragment.evolve(
                        staging_hints=hints.model_copy(
                            update={"media_timing": music.staging_hints.media_timing},
                        ),
                    )
                music = fragment
        elif (
            isinstance(fragment, ControlFragment)
            and music is not None
            and fragment.matches(music)
        ):
            if fragment.fragment_type == "delete":
                music = None
            elif fragment.media_action is None:
                music = music.evolve(**{**fragment.payload, "uid": music.uid})
                if music.media_role != "music":
                    music = None
    return music
