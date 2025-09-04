
from tangl.lang.body_parts import BodyPart
from tangl.mechanics.look.ornaments import Ornamentation, Ornament, OrnamentType

import pytest

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


@pytest.mark.xfail(reason="Need to write", raises=NotImplementedError)
def test_ornament_details():
    # todo: - visibility by outfit coverage
    #       - desc by part vs. by type
    raise NotImplementedError
