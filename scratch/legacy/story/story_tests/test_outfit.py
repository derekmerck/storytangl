import pydantic
import pytest

from tangl.graph import Node
from tangl.story.asset.wearable import WearableLayer, WearableType, Wearable, BodyRegion, WearableState
from tangl.story.actor.outfit import OutfitManager, HasOutfit, OutfitHandler
# from tangl.lang.anthrocentric import BodyPart
from tangl.lang.nominal import DeterminativeType as DT

TestOutfitNode = pydantic.create_model("TestOutfitNode", __base__=(HasOutfit, Node))

@pytest.fixture
def wearables():

    WearableType.clear_instances()

    # Creating instances of WearableType
    coat  = WearableType(label='coat',  covers={BodyRegion.UPPER}, layer=WearableLayer.OVER)
    shirt = WearableType(label='shirt', covers={BodyRegion.UPPER}, layer=WearableLayer.OUTER, noun='shirt')
    pants = WearableType(label='pants', covers={BodyRegion.LOWER}, layer=WearableLayer.OUTER, noun='pants')
    socks = WearableType(label='socks', covers={BodyRegion.FEET}, layer=WearableLayer.INNER)
    shoes = WearableType(label='shoes', covers={BodyRegion.FEET}, layer=WearableLayer.OUTER, noun='shoes')
    dress = WearableType(label='dress', covers={BodyRegion.LOWER, BodyRegion.UPPER}, layer=WearableLayer.OUTER, noun='dress')
    exclusive_dress = WearableType(label='exclusive_dress', ref='dress', tags={'exclusive'})

    yield Wearable(coat), Wearable(shirt), Wearable(pants), Wearable(socks), Wearable(shoes), Wearable(dress), Wearable(exclusive_dress)

    # teardown - restore wearables to original state
    WearableType.load_instances_from_yaml()

@pytest.fixture
def outfit_node(wearables):
    coat, shirt, pants, socks, shoes, dress, exclusive_dress = wearables

    node = TestOutfitNode()
    for ww in [coat, shirt, pants, socks, shoes]:
        node.add_child(ww)
    return node

def test_render(outfit_node):
    # Render the outfit description
    outfit_desc = outfit_node.outfit.render_desc()
    print( outfit_desc )
    assert 'coat' in outfit_desc
    assert 'shirt' not in outfit_desc  # covered by jacket
    assert 'pants' in outfit_desc

    outfit_node.outfit.open('coat')
    outfit_desc = outfit_node.outfit.render_desc()
    print( outfit_desc )
    assert 'coat' in outfit_desc
    assert 'shirt' in outfit_desc  # exposed by open jacket
    assert 'pants' in outfit_desc

def test_wearable_state():

    print( WearableState )
    print( WearableState.__members__ )
    assert WearableState('open') is WearableState.OPEN


def test_wearable_state_handler_is_visible(outfit_node):

    # Shirt should be invisible because the coat is on and covers it
    assert not OutfitHandler.is_visible(outfit_node, 'shirt')

    # Now open the jacket
    OutfitHandler.transition(outfit_node, 'coat', WearableState.OPEN)
    # Shirt should now be not visible because the jacket is off
    assert OutfitHandler.is_visible(outfit_node, 'shirt')

    # Take the jacket off
    OutfitHandler.transition(outfit_node, 'coat', WearableState.OFF)
    # Shirt should still be visible because the jacket is off and covers it
    assert OutfitHandler.is_visible(outfit_node, 'shirt')



#
# def test_wearable():
#
#     thneed = Wearable(label="thneed",
#                       nouns=["thnead"],
#                       color="blue",
#                       covers=[BodyRegion.TOP, BodyRegion.BOTTOM])
#     green_thneed = Wearable(label="green_thneed",
#                             color="green",
#                             referent="thneed")
#     #
#     # assert green_thneed.nouns == thneed.nouns
#     # assert green_thneed.color == "green"
#
#
# def test_put_on(outfit, wearables):
#     tshirt, jeans, jacket = wearables
#     print( outfit )
#     # Initially, the wearables are ON
#     assert outfit.wearables[tshirt] == outfit.wearables[jeans] == outfit.wearables[jacket] == WearableState.ON
#
#     # Can't take off t-shirt yet
#     with pytest.raises(ValueError):
#         outfit.take_off(tshirt)
#         assert outfit.wearables[tshirt] == WearableState.OFF
#
#     # Take off the jacket first
#     outfit.take_off(jacket)
#
#     # Then can take off the tshirt
#     outfit.take_off(tshirt)
#
#     # Try to put on the t-shirt
#     outfit.put_on(tshirt)
#     assert outfit.wearables[tshirt] == WearableState.ON
#
# def test_open(outfit, wearables):
#     tshirt, jeans, jacket = wearables
#     # Try to open the jacket
#     outfit.open(jacket)
#     assert outfit.wearables[jacket] == WearableState.OPEN
#
# def test_take_off(outfit, wearables):
#     tshirt, jeans, jacket = wearables
#     # Try to take off the jeans
#     outfit.take_off(jeans)
#     assert outfit.wearables[jeans] == WearableState.OFF
#
# # Test cases for WearableStateHandler methods
#
# def test_can_transition(outfit, wearables):
#     tshirt, jeans, jacket = wearables
#     # Check that tshirt can not transition to OFF state b/c of jacket
#     assert not outfit.state_handler.can_transition(tshirt, WearableState.OFF)
#
#     # Check that tshirt can not transition to OPEN state b/c of jacket
#     assert not outfit.state_handler.can_transition(tshirt, WearableState.OPEN)
#
#     # Check that tshirt still cannot transition to OFF state but _can_
#     # transition to OPEN state if jacket is OPEN
#     outfit.open(jacket)
#     assert not outfit.state_handler.can_transition(tshirt, WearableState.OFF)
#     assert outfit.state_handler.can_transition(tshirt, WearableState.OPEN)
#
# def test_transition(outfit, wearables):
#     tshirt, jeans, jacket = wearables
#     # Transition tshirt to OFF state
#     outfit.state_handler.transition(jacket, WearableState.OFF)
#     assert outfit.wearables[jacket] == WearableState.OFF
#
#     with pytest.raises(ValueError):
#         # can't go straight to open
#         outfit.state_handler.transition(jacket, WearableState.OPEN)
#
#     outfit.state_handler.transition(jacket, WearableState.ON)
#     outfit.state_handler.transition(jacket, WearableState.OPEN)
#     assert outfit.wearables[jacket] == WearableState.OPEN
#
# def test_add_item(outfit):
#     # Create a new wearable
#     hat = Wearable(label='hat', layer=WearableLayer.OUTER, covers={BodyRegion.TOP})
#
#     # Add it to the outfit
#     outfit.state_handler.add_item(hat)
#     assert hat in outfit.wearables
#
# def test_discard_item(outfit, wearables):
#     tshirt, jeans, jacket = wearables
#     # Discard the tshirt from the outfit
#     outfit.state_handler.discard_item(tshirt)
#     assert tshirt not in outfit.wearables
