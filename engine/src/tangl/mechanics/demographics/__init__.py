"""Demographic profile resources and actor-facing facet helpers.

Why
---
This family supplies demographic catalogs plus a thin mixin surface for story
entities that want sampled or authored identity details without introducing a
parallel mechanics runtime.

Key Features
------------
* Resource-backed :class:`Region`, :class:`Country`, :class:`Subtype`, and
  :class:`NameBank` models.
* :class:`DemographicSampler` for controlled profile sampling.
* :class:`HasDemographics` facet for publishing actor identity into local
  namespaces.
"""

__version__ = "3.0.0"
__title__ = "StoryTangl DemographicForge"

from .data_models import Country, NameBank, Region, Subtype, load_demographic_distributions
from .demographic import DemographicData, HasDemographic, HasDemographics
from .sampler import DemographicSampler

__all__ = [
    "Country",
    "DemographicData",
    "DemographicSampler",
    "HasDemographic",
    "HasDemographics",
    "NameBank",
    "Region",
    "Subtype",
    "load_demographic_distributions",
]
