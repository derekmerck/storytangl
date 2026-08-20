"""Catalog definitions and graph-owned badge repertoires for call-response games."""

from __future__ import annotations

from typing import ClassVar

from pydantic import ConfigDict

from tangl.core import Singleton, Token
from tangl.mechanics.assembly import ComponentManager, Slot

from .call_response_game import PhraseRole


KNOWN_PHRASES_SLOT = "known_phrases"


class PhraseType(Singleton):
    """Immutable catalog definition for one call-response phrase.

    Why
    ---
    Phrase text and role capability are semantic catalog truth, while earned
    instances remain mutable graph-owned badges.

    Key Features
    ------------
    - Stores the phrase's display text and allowed call/response roles.
    - Retains the ordinary singleton tag surface for world-authored catalogs.

    API
    ---
    Use :class:`PhraseBadge` for a graph-owned earned instance.

    Notes
    -----
    A selected :class:`~tangl.core.TokenCatalog` bounds a world's available
    definitions; this class does not enumerate or own a catalog.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    text: str
    roles: tuple[PhraseRole, ...]


class PhraseBadgeToken(Token):
    """Named token base for graph-owned phrase badges.

    Why
    ---
    Keeps the public badge wrapper stable if later repertoire work needs
    badge-local behavior.

    Key Features
    ------------
    - Separates the public badge class from the generic token wrapper.

    API
    ---
    :class:`PhraseBadge` is the generated wrapper bound to :class:`PhraseType`.

    Notes
    -----
    The base adds no local policy; ordinary token and component ownership
    semantics remain authoritative.

    See also
    --------
    :class:`RepertoireManager`
        Owner-bound storage for earned badges.
    """


PhraseBadge = PhraseBadgeToken._create_wrapper_cls(PhraseType, "PhraseBadge")


class RepertoireManager(ComponentManager[PhraseBadge]):
    """Owner-bound collection of earned phrase badges.

    Why
    ---
    Reuses ordinary component ownership and transfer semantics rather than
    making learned phrases a special inventory or registry.

    Key Features
    ------------
    - Persists badge membership by graph UUID through ``ComponentManager``.
    - Exposes one large ``known_phrases`` slot for later contest snapshots.

    API
    ---
    :meth:`badges`, :meth:`phrase_ids`, and :meth:`has_phrase` expose the
    small read surface needed by the following composition slice.
    """

    slots: ClassVar[dict[str, Slot]] = {
        KNOWN_PHRASES_SLOT: Slot.for_type(
            KNOWN_PHRASES_SLOT,
            PhraseBadge,
            max_count=1000,
        ),
    }

    def badges(self) -> list[PhraseBadge]:
        """Return known badges in stable definition/id order."""

        return sorted(
            self.get_slot(KNOWN_PHRASES_SLOT),
            key=lambda badge: (badge.token_from, str(badge.uid)),
        )

    def phrase_ids(self) -> list[str]:
        """Return known phrase-definition identifiers in badge order."""

        return [badge.token_from for badge in self.badges()]

    def has_phrase(self, phrase_id: str) -> bool:
        """Return whether this repertoire currently owns a matching badge."""

        return phrase_id in self.phrase_ids()
