from __future__ import annotations

from typing import Dict, Mapping, Optional

from pydantic import BaseModel, ConfigDict

from ..definition.stat_system import StatSystemDefinition
from ..stats.stat import Stat


class StatContext(BaseModel):
    """
    Minimal context stub that donates a StatSystemDefinition
    and can create stat dicts consistent with that system.

    Intended as a stand-in for a “world” or “domain” object
    that knows which stat schema to use.
    """

    model_config = ConfigDict(extra="allow")

    stat_system: StatSystemDefinition

    def make_stats(
        self,
        *,
        base_fv: float = 10.0,
        overrides: Optional[Mapping[str, float | int | str]] = None,
    ) -> Dict[str, Stat]:
        """
        Create a new dict[name -> Stat] consistent with this context's stat_system.

        Parameters
        ----------
        base_fv:
            Default fv for stats not in overrides.
        overrides:
            Optional mapping of stat_name -> value (fv or qv-like).

        Returns
        -------
        dict[str, Stat]
        """
        overrides = overrides or {}
        stats: Dict[str, Stat] = {}
        for sdef in self.stat_system.stats:
            value = overrides.get(sdef.name, base_fv)
            stats[sdef.name] = Stat(value)
        return stats
