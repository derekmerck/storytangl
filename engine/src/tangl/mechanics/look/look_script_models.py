
# class OutfitScript(NodeScript):
#     palette: Optional[str] = None
#     outfit_type: Optional[str] = None
#     wearables: list[ UniqueLabel | AssetScript ] = None

class OrnamentationScript(BaseScriptItem):
    ornaments: list[str]

class LookScript(BaseScriptItem, extra="allow"):
    hair_style: Optional[HairStyle] = None
    hair_color: Optional[HairColor] = None
    hair_kws: Optional[str] = None   # for stableforge

    eye_color: Optional[EyeColor] = None

    skin_color: Optional[SkinColor] = None
    body_shape: Optional[BodyShape] = None  # banana, apple, pear, hourglass
    sz: Optional[float] = None
    br: Optional[float] = None
    fit: Optional[float] = None

    # body_type: Optional[BodyType]
    # short_stack, willowy, voluptuous, top_heavy, loli, cut etc.
    # can infer from shape + params

    pretty: Optional[float] = None
    apparent_age: Optional[ApparentAge] = None
    reference_model: Optional[str] = None

    outfit_type: Optional[str] = None
    glasses: Optional[bool] = None
    outfit_kws: Optional[str] = None    # for stableforge
    outfit_palette: Optional[str] = None
