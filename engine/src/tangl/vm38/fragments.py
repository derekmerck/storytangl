# tangl/vm38/fragments.py
"""Minimal fragment types for the VM journal phase.

The phase pipeline's JOURNAL step produces fragments — small records that
capture rendered content, choices, or other narrative output. The VM layer
defines only the base type; the story layer can extend it.

All fragments are Records, so they participate in ``OrderedRegistry`` append
and can be serialized/deserialized through the standard ``unstructure`` path.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from tangl.core38 import Record


__all__ = [
    "Fragment",
    "ContentFragment",
    "ChoiceFragment",
]


class Fragment(Record):
    """Base record emitted by the JOURNAL phase."""

    fragment_type: str = "fragment"
    step: int = -1


class ContentFragment(Fragment):
    """A rendered text fragment emitted by the JOURNAL phase.

    Parameters
    ----------
    content
        The rendered text (post-template, post-substitution).
    source_id
        UID of the node that produced this fragment.
    fragment_type
        Discriminator for story-layer dispatch.
    step
        The cursor_steps value when this fragment was emitted.
        Enables ``get_journal(since_step=...)`` filtering.
    """

    content: str = ""
    source_id: Optional[UUID] = None
    fragment_type: str = "content"


class ChoiceFragment(Fragment):
    """A choice presented to the player, emitted alongside content.

    Parameters
    ----------
    edge_id
        UID of the edge this choice follows.
    text
        Display text for the choice.
    available
        Whether the choice is currently traversable.
    """

    edge_id: Optional[UUID] = None
    text: str = ""
    available: bool = True
    fragment_type: str = "choice"
