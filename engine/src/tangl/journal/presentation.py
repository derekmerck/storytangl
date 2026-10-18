"""Read-only projection of canonical journal intent, not playback state."""

from __future__ import annotations

from collections.abc import Iterable

from tangl.core import BaseFragment

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
                music = fragment.continued_from(music)
        elif isinstance(fragment, ControlFragment) and music is not None:
            updated = fragment.apply_to(music)
            music = updated if (
                isinstance(updated, MediaFragment)
                and updated.media_role == "music" and updated.rit_id is not None
            ) else None
    return music
