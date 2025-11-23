from __future__ import annotations

from typing import FrozenSet, Iterable, Optional, Set

from pydantic import BaseModel, ConfigDict, Field


class SituationalEffect(BaseModel):
    """
    A tag- and stat-scoped situational modifier.

    Typical usage:
        sword = SituationalEffect(
            name="Sword of Kings",
            applies_to_tags={"#combat"},
            applies_to_stats={"body"},
            difficulty_modifier=-0.5,
        )

        crowd_support = SituationalEffect(
            name="Cheering Crowd",
            applies_to_tags={"#arena"},
            competency_modifier=1.0,
        )

    Semantics
    ---------
    - `applies_to_tags`:
        The effect is *eligible* if this set is empty OR it intersects
        the scenario tags (e.g., {"#combat", "#night"}).
    - `applies_to_stats`:
        The effect is *eligible* for a given stat if this set is empty
        OR it contains that stat name.

    Modifiers
    ---------
    - `difficulty_modifier`:
        Additive adjustment to difficulty (delta = competency - difficulty).
    - `competency_modifier`:
        Additive adjustment to competency.
    """

    model_config = ConfigDict(frozen=True)

    name: Optional[str] = None

    applies_to_tags: FrozenSet[str] = Field(default_factory=frozenset)
    applies_to_stats: FrozenSet[str] = Field(default_factory=frozenset)

    difficulty_modifier: float = 0.0
    competency_modifier: float = 0.0

    def applies(
        self,
        *,
        tags: Iterable[str] | None = None,
        stat_name: str | None = None,
    ) -> bool:
        """
        Return True if this effect applies given scenario tags and stat.

        Rules
        -----
        - If `applies_to_tags` is non-empty, it must intersect `tags`.
        - If `applies_to_stats` is non-empty and `stat_name` is not None,
          it must contain `stat_name`.
        """
        tag_set: Set[str] = set(tags or ())

        # Tag gate
        if self.applies_to_tags and not (self.applies_to_tags & tag_set):
            return False

        # Stat gate
        if self.applies_to_stats and stat_name is not None:
            if stat_name not in self.applies_to_stats:
                return False

        return True
