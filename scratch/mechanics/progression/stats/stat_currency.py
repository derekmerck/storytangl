from typing import ClassVar, Type
from enum import Enum

from tangl.story.asset.fungible import Fungible

class StatCurrency(Fungible):
    base_stat: Enum
