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

from .data_models import Country, NameBank, NameForm, NamePart, NamePool, Region, Subtype
from .packs import (
    DemographicPack,
    PackMetadata,
    PackUnavailableError,
    load_pack,
    parse_pack,
    register_pack,
)
from .demographic import DemographicData, HasDemographics
from .sampler import DemographicSampler
from .selection import NameSelection, Origin, name_catalog, select_bank, select_origin

from .generation import GenerationRequest, GenerationReceipt, complete_generation

__all__ = [
    "Country",
    "GenerationRequest",
    "GenerationReceipt",
    "complete_generation",
    "NameSelection",
    "Origin",
    "name_catalog",
    "select_bank",
    "select_origin",
    "DemographicData",
    "DemographicSampler",
    "HasDemographics",
    "NameBank",
    "NameForm",
    "NamePart",
    "NamePool",
    "Region",
    "Subtype",
    "DemographicPack",
    "PackMetadata",
    "PackUnavailableError",
    "load_pack",
    "parse_pack",
    "register_pack",
]
