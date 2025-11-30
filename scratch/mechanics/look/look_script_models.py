from typing import Optional

from tangl.type_hints import UniqueLabel
from tangl.lang.age_range import AgeRange
from tangl.ir.core_ir import BaseScriptItem
from .enums import HairColor, HairStyle, EyeColor, SkinTone, BodyPhenotype

AssetScript = BaseScriptItem

class OutfitScript(BaseScriptItem, extra="allow"):
    palette: Optional[str] = None
    outfit_type: Optional[str] = None
    wearables: list[ UniqueLabel | AssetScript ] = None

class OrnamentationScript(BaseScriptItem):
    ornaments: list[str]

class LookScript(BaseScriptItem, extra="allow"):
    hair_style: Optional[HairStyle] = None
    hair_color: Optional[HairColor] = None
    hair_kws: Optional[str] = None   # for stableforge
    eye_color: Optional[EyeColor] = None

    skin_tone: Optional[SkinTone] = None
    body_phenotype: Optional[BodyPhenotype] = None
    fit: Optional[float] = None   # fitness for inferring body-phenotype
    size: Optional[float] = None  # multiplier for relative rendering scale

    apparent_age: Optional[AgeRange] = None
    reference_model: Optional[str] = None

    # HasOutfit mixin
    outfit: Optional[OutfitScript] = None
    glasses: Optional[bool] = None      # override, if glasses in outfit, can be removed
    outfit_kws: Optional[str] = None    # for stableforge
    outfit_palette: Optional[str] = None
