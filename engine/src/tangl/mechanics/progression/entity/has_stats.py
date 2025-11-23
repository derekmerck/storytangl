from __future__ import annotations

from typing import Dict, Iterable, Mapping, Optional

from pydantic import BaseModel, ConfigDict

from ..definition.stat_system import StatSystemDefinition
from ..stats.stat import Stat


class HasStats(BaseModel):
    """
    Mixin/base for entities that have a stat block.

    Attributes
    ----------
    stat_system:
        The stat schema used to interpret and initialize stats.
    stats:
        Mapping from stat name → Stat instance.

    Notes
    -----
    - Does *not* depend on any graph/VM types.
    - Provides dynamic attribute access:

        entity.body  → entity.stats["body"]
        entity.mind  → entity.stats["mind"]

      If an attribute is not found in the normal fields, we look it up
      in `stats`. Unknown attributes still raise AttributeError.
    """

    model_config = ConfigDict(extra="allow")

    stat_system: StatSystemDefinition
    stats: Dict[str, Stat]

    # ------------------------------------------------------------------ #
    # Constructors
    # ------------------------------------------------------------------ #

    @classmethod
    def from_system(
        cls,
        stat_system: StatSystemDefinition,
        *,
        base_fv: float = 10.0,
        overrides: Optional[Mapping[str, float | int | str]] = None,
        **extra,
    ) -> "HasStats":
        """
        Construct an instance with stats populated from a StatSystemDefinition.

        Parameters
        ----------
        stat_system:
            The stat schema to use.
        base_fv:
            Default fv for any stat not in overrides.
        overrides:
            Optional mapping of stat_name → value (fv or qv/Quality-like).
        extra:
            Extra fields for subclasses (name, uid, etc.).

        Returns
        -------
        HasStats
            An instance with all stats defined by `stat_system`.
        """
        overrides = overrides or {}
        stats: Dict[str, Stat] = {}

        for sdef in stat_system.stats:
            value = overrides.get(sdef.name, base_fv)
            stats[sdef.name] = Stat(value)

        return cls(stat_system=stat_system, stats=stats, **extra)

    # ------------------------------------------------------------------ #
    # Access helpers
    # ------------------------------------------------------------------ #

    def get_stat(self, name: str) -> Stat:
        """Get a Stat by name, raising KeyError if missing."""
        return self.stats[name]

    def set_stat(self, name: str, value: float | int | str) -> None:
        """Set or create a Stat by name using Stat's flexible constructor."""
        self.stats[name] = Stat(value)

    def iter_stats(self, names: Optional[Iterable[str]] = None):
        """Iterate over (name, Stat) pairs; optionally constrained to a subset of names."""
        if names is None:
            yield from self.stats.items()
        else:
            for n in names:
                if n in self.stats:
                    yield n, self.stats[n]

    # ------------------------------------------------------------------ #
    # Competency helper
    # ------------------------------------------------------------------ #

    def compute_competency(self, domain: Optional[str]) -> float:
        """
        Compute competency for a given domain according to the system's intrinsic_map.

        Rules
        -----
        - If domain is None: return average fv across *intrinsic* stats, or 10.0 if none.
        - If domain is intrinsic (and has a Stat): competency = fv(domain).
        - If domain is governed_by an intrinsic: competency = average(intrinsic.fv, domain.fv).
        - If domain is unknown: 10.0 (neutral fallback).
        """
        if domain is None:
            intrinsic_names = [s.name for s in self.stat_system.intrinsics]
            if not intrinsic_names:
                return 10.0
            values = [self.stats[n].fv for n in intrinsic_names if n in self.stats]
            return sum(values) / len(values) if values else 10.0

        if any(s.name == domain and s.is_intrinsic for s in self.stat_system.intrinsics):
            stat = self.stats.get(domain)
            return stat.fv if stat else 10.0

        intrinsic_map = self.stat_system.intrinsic_map
        governor_name = intrinsic_map.get(domain)
        domain_stat = self.stats.get(domain)
        governor_stat = self.stats.get(governor_name) if governor_name else None

        if domain_stat and governor_stat:
            return (domain_stat.fv + governor_stat.fv) / 2.0
        if domain_stat:
            return domain_stat.fv

        return 10.0

    # ------------------------------------------------------------------ #
    # Dynamic attribute access
    # ------------------------------------------------------------------ #

    def __getattr__(self, item: str):
        """
        If attribute not found on the model, try to resolve it as a stat name.

        This allows hero.body instead of hero.stats["body"].

        IMPORTANT: Only called for attributes that aren't fields, so normal
        BaseModel behavior is preserved.
        """
        stats = self.__dict__.get("stats", {})
        if isinstance(stats, dict) and item in stats:
            return stats[item]
        raise AttributeError(f"{type(self).__name__!s} has no attribute {item!r}")
