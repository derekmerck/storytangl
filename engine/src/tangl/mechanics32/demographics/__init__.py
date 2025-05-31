"""
This package provides classes and functions for generating and handling demographic data for NPCs (Non-Player Characters) in a game.

The demographic_data module includes the following classes:

- `CountryData`: A dataclass representing the demographic data for a country.
- `RegionData`: A dataclass representing the demographic data for a region.

The enums module includes these definitions:

- `_Enum`: An Enum class with additional methods for generating random instances based on different distributions.
- `Region`: An Enum class representing a region.
- `Country`: An Enum class representing a country.
- `Subtype`: An Enum class representing ethnic subtypes within a country or region.
- `Gens`: An Enum class representing the two possible genders.

NameSampler and DemographicSampler provide data sampling and default management.

DemographicFactory provides a convenience class factory method for Demographic instances.

The module also depends on the following functions:

- `load_yaml_resource`: A function for loading YAML resources, with caching functionality to improve performance.

A wrapper for a `faker` provider library can be used with Faker to generate names, nationalities, and other attributes for NPCs.
"""
__version__ = "3.0.0"
__title__ = "StoryTangl DemographicForge"

from .sampler import DemographicSampler, DemographicData

