"""
This is an abstract framework for a progression activity interaction.
It is intended to be extended and specified under alternate progression
systems, ie, quality measurements and domains.
"""

from .measures import Quality
from .stats import Stat
from .stat_domain_map import StatDomainMap, HasStats
