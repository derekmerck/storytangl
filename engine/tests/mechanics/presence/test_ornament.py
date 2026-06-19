import pytest

from tangl.lang.body_parts import BodyPart, BodyRegion
from tangl.mechanics.presence.ornaments import Ornamentation, Ornament, OrnamentType
from tangl.mechanics.presence.outfit import OutfitManager
from tangl.mechanics.presence.wearable import Wearable, WearableLayer, WearableType


@pytest.fixture(autouse=True)
def reset_wearable_types():
    WearableType.clear_instances()
    yield
    WearableType.clear_instances()


def test_ornaments():

    o0 = Ornament( body_part = BodyPart.FACE,
                   ornament_type = OrnamentType.SCAR,
                   text = "a grim scar")
    o1 = Ornament( body_part = BodyPart.RIGHT_ARM,
                   ornament_type = OrnamentType.TATTOO,
                   text = "a dragon")

    orn = Ornamentation()
    assert not orn

    orn.add_ornament(o0)
    orn.add_ornament(o1)

    assert orn

    s = orn.describe()['ornaments']
    print( s )
    assert "scars" in s
    assert "dragon" in s

    o2 = Ornament( body_part=BodyPart.ABDOMEN, ornament_type= OrnamentType.PIERCING, text="a navel ring in" )
    o3 = Ornament( body_part=BodyPart.FACE, ornament_type= OrnamentType.BURN, text="a nasty burn")
    o4 = Ornament( body_part=BodyPart.LEFT_BUTTOCK, ornament_type=OrnamentType.BRAND, text="your house sigil")
    orn.add_ornament( o2 )
    orn.add_ornament( o3 )
    orn.add_ornament( o4 )

    s = orn.describe()['ornaments']
    print( s )
    assert "scars" in s
    assert "dragon" in s
    assert "navel" in s
    assert "brand" in s

    orn.remove_ornament( o4 )
    s = orn.describe()['ornaments']
    print( s )
    assert "scars" in s
    assert "dragon" in s
    assert "navel" in s
    assert not "brand" in s


def test_ornament_descriptions_are_neutral_and_filter_covered_regions():
    face_scar = Ornament(
        body_part=BodyPart.FACE,
        ornament_type=OrnamentType.SCAR,
        text="a grim scar",
    )
    arm_tattoo = Ornament(
        body_part=BodyPart.RIGHT_ARM,
        ornament_type=OrnamentType.TATTOO,
        text="a dragon",
    )

    assert "their" in arm_tattoo.describe()

    orn = Ornamentation(collection=[face_scar, arm_tattoo])
    visible = orn.by_part_type([BodyRegion.TOP])

    assert (OrnamentType.TATTOO, BodyPart.RIGHT_ARM) not in visible
    assert (OrnamentType.SCAR, BodyPart.FACE) in visible
    assert orn.describe()["ornaments"].startswith("They have ")


def test_covered_mask_hides_arm_tattoo_but_not_face_mark() -> None:
    face_scar = Ornament(
        body_part=BodyPart.FACE,
        ornament_type=OrnamentType.SCAR,
        text="a grim scar",
    )
    arm_tattoo = Ornament(
        body_part=BodyPart.RIGHT_ARM,
        ornament_type=OrnamentType.TATTOO,
        text="a dragon",
    )
    ornaments = Ornamentation(collection=[face_scar, arm_tattoo])

    summary = ornaments.describe_summary(covered_mask=BodyPart.TOP)

    assert "scars" in summary
    assert "dragon" not in summary


def test_outfit_coverage_hides_arm_tattoo_but_not_face_mark() -> None:
    shirt_type = WearableType(
        label="ornament_test_shirt",
        noun="shirt",
        covers={BodyRegion.TOP},
        layer=WearableLayer.OUTER,
    )
    outfit = OutfitManager()
    outfit.assign("top_60", Wearable(token_from=shirt_type.label))

    ornaments = Ornamentation(
        collection=[
            Ornament(
                body_part=BodyPart.FACE,
                ornament_type=OrnamentType.MARKER,
                text="a blue crescent",
            ),
            Ornament(
                body_part=BodyPart.RIGHT_ARM,
                ornament_type=OrnamentType.TATTOO,
                text="a dragon",
            ),
        ]
    )

    assert outfit.covered_mask() == BodyPart.TOP
    assert outfit.covered_regions() == [BodyRegion.TOP]

    summary = ornaments.describe_summary(covered_mask=outfit.covered_mask())

    assert "crescent" in summary
    assert "dragon" not in summary
