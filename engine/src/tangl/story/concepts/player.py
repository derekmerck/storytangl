from __future__ import annotations

from typing import Any

from pydantic import Field

from tangl.core import Node, contribute_ns
from tangl.type_hints import Tag


class Player(Node):
    """Player()

    Non-structural protagonist node published as a high-scope namespace fixture.

    Why
    ----
    Some stories have a single point-of-view actor whose accumulated state
    (inventory, storyline flags, mood, achievements) gates and colours later
    events. ``Player`` gives that actor a stable home in the runtime graph
    without making it part of the cursor-traversal fabric: it is a provider
    node, like :class:`Actor`, that publishes itself into the scoped runtime
    namespace so authored ``conditions``/``availability`` predicates can read
    it directly (``player.has('sword')``).

    Not every story has a protagonist, so ``Player`` is never injected
    automatically; a world that wants one declares it (today by composing a
    world subclass into its bundle; a generic world-level declaration API is
    intentionally deferred).

    Key Features
    ------------
    * Publishes ``{"player": self, "flags": ..., "mood": ...}`` through the
      existing :func:`contribute_ns` mechanism -- no new namespace machinery.
    * Unifies the activator query surface: :meth:`has` matches over tags,
      inventory, storyline flags, and achievements with one call.

    API
    ---
    - :attr:`inv` discrete possessions (tag-like items).
    - :attr:`flags` storyline/progression flags set by events.
    - :attr:`achievements` durable accomplishments.
    - :attr:`mood` optional current disposition (read by effect authors).
    - :meth:`has` true if every queried item is a tag, inventory entry,
      flag, or achievement.
    - :meth:`provide_player_symbols` the namespace payload this node
      contributes.
    """

    label: str = "player"

    full_name: str = ""
    mood: str | None = None

    # ``include=True``: event handlers mutate these in place
    # (``player.inv.add(...)``) without reassigning the field; the marker keeps
    # non-default values in ``unstructure()`` snapshots while still eliding
    # empty defaults.
    inv: set[Tag] = Field(default_factory=set, json_schema_extra={"include": True})
    flags: set[Tag] = Field(default_factory=set, json_schema_extra={"include": True})
    achievements: set[Tag] = Field(
        default_factory=set, json_schema_extra={"include": True}
    )

    def has(self, *items: Tag) -> bool:
        """Return True when every queried item is owned, flagged, or earned."""
        owned = set(self.tags or ()) | self.inv | self.flags | self.achievements
        return set(items).issubset(owned)

    @contribute_ns
    def provide_player_symbols(self) -> dict[str, Any]:
        """Publish the protagonist into local namespace contribution."""
        return {
            "player": self,
            "flags": self.flags,
            "mood": self.mood,
        }
