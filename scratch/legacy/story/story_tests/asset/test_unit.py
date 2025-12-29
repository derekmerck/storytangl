from typing import *

from tangl.asset import Unit, Squad
from tangl.asset.unit import stone, iron, glass, UnitAlignment

import pytest

# @pytest.mark.skip(reason="Use SingletonsManager for namespace isolation instead")
# def test_unit_factory():
#
#     # Clear any existing entries
#     Unit._instances = dict()
#
#     from tangl.entity import EntityFactory
#     F = EntityFactory()
#     F.add_entity_class(Unit)
#     F.add_template(Unit, **paper_ )
#     F.add_template(Unit, **rock_ )
#
#     paper = F.new_entity("Unit", "paper")
#
#     print( paper )
#
#     # Create a private class, note that attrs.make_class does _not_ work
#     import attr
#     @attr.define( slots=False, eq=False, hash=False, init=False )
#     class Unit_( Unit ):
#         _instances:  ClassVar[dict] = dict()
#         pass
#
#     Unit_.__init_entity_subclass__()
#
#     F.add_entity_class(Unit_, "Unit")
#
#     rock = F.new_entity("Unit", "rock")
#     rock.__init__()
#
#     print( rock )
#
#     print( Unit._instances )
#     assert paper in Unit._instances.values()
#     assert rock not in Unit._instances.values()
#
#     print( Unit_._instances )
#     assert paper not in Unit_._instances.values()
#     assert paper not in Unit_._instances.values()
#
#     assert Unit_.instance("paper") == paper
#     assert Unit_.instance("rock") == rock
#
#     from tangl.utils.singleton import Singletons
#     print( Singletons._instances )
#     assert paper not in Singletons._instances.values()
#     assert rock not in Singletons._instances.values()


# @pytest.mark.skip(reason="no world yet")
# def test_unit_loader():
#
#     Unit(**hob_)
#     assert( "hob" in Unit._instances )
#
#     from tangl.world import World
#     wo = World.load_world( "../scratch/worlds/TestWorld" )
#
#     assert( "hob" not in wo.units._instances )
#     assert( "hob" in Unit._instances )
#
#     assert( "mech" in wo.units._instances )
#     assert( "mech" not in Unit._instances )


if __name__ == "__main__":
    test_units()

from typing import *

from tangl.game import RpsMove
from tangl.asset import Unit, UnitGroup

import pytest


@pytest.mark.skip(reason="Use SingletonsManager for namespace isolation instead")
def test_unit_factory():

    # Clear any existing entries
    Unit._instances = dict()

    from tangl.entity import EntityFactory
    F = EntityFactory()
    F.add_entity_class(Unit)
    F.add_template(Unit, **paper_ )
    F.add_template(Unit, **rock_ )

    paper = F.new_entity("Unit", "paper")

    print( paper )

    # Create a private class, note that attrs.make_class does _not_ work
    import attr
    @attr.define( slots=False, eq=False, hash=False, init=False )
    class Unit_( Unit ):
        _instances:  ClassVar[dict] = dict()
        pass

    Unit_.__init_entity_subclass__()

    F.add_entity_class(Unit_, "Unit")

    rock = F.new_entity("Unit", "rock")
    rock.__init__()

    print( rock )

    print( Unit._instances )
    assert paper in Unit._instances.values()
    assert rock not in Unit._instances.values()

    print( Unit_._instances )
    assert paper not in Unit_._instances.values()
    assert paper not in Unit_._instances.values()

    assert Unit_.instance("paper") == paper
    assert Unit_.instance("rock") == rock

    from tangl.utils.singleton import Singletons
    print( Singletons._instances )
    assert paper not in Singletons._instances.values()
    assert rock not in Singletons._instances.values()


# @pytest.mark.skip(reason="no world yet")
# def test_unit_loader():
#
#     Unit(**hob_)
#     assert( "hob" in Unit._instances )
#
#     from tangl.world import World
#     wo = World.load_world( "../scratch/worlds/TestWorld" )
#
#     assert( "hob" not in wo.units._instances )
#     assert( "hob" in Unit._instances )
#
#     assert( "mech" in wo.units._instances )
#     assert( "mech" not in Unit._instances )


if __name__ == "__main__":
    pass
