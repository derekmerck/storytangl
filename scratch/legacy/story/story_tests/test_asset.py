import logging

import pytest

from tangl.core.entity import Node
from tangl.story.concepts.asset import AssetType, DiscreteAsset as Asset


@pytest.fixture(autouse=True)
def _clear_asset_type():
    AssetType.clear_instances()


def test_asset_type_singleton():
    a = AssetType(label="a")

    print('created')

    # fetchable
    assert AssetType.get_instance('a') is a

    print('passed')

    # unique
    with pytest.raises(KeyError):
        b = AssetType(label="a")
        assert b is a

    # hashes
    { a }


def test_asset():

    asset = Asset(label="asset1", text="A shiny sword")

    assert hasattr(asset, 'parent')
    assert asset.label == "asset1"

    assert hasattr(asset, 'text')
    assert asset.text == "A shiny sword"

    rendered_description = asset.render()
    logging.debug(rendered_description)
    assert rendered_description.get('text') == "A shiny sword"

    asset = Asset(label="asset2", text="{{ metal.capitalize() }} Sword", locals={"metal": "golden"} )
    assert asset.label == "asset2"

    assert asset.render().get('text') == "Golden Sword"


def test_asset_pickles():
    import pickle
    a = Asset(label="abc")

    s = pickle.dumps(a)
    res = pickle.loads(s)
    print(res)
    assert a == res


# @pytest.mark.skip(reason="Not working")
def test_referent_asset():
    base_asset = Asset(label="base_asset", text="base asset text")
    derived_asset = Asset(label="derived_asset", from_ref="base_asset")
    assert base_asset.text == derived_asset.text

    # hashes
    { base_asset }


# OwnerNode = attr.make_class("OwnerNode", (), (Owner, Node))
#
# def test_has_assets():
#
#     Asset._instances.clear()
#
#     owner = OwnerNode()
#     asset = Asset(label="asset1", text="A shiny sword")
#     assert asset not in owner.owned
#
#     owner.add_child(asset)
#     assert len(list(owner.owned)) == 1
#     assert asset in owner.owned
#     assert asset in owner.ns()['owned']
#
#     owner.remove_child(asset)
#     assert len(list(owner.owned)) == 0
#     assert asset not in owner.ns()['owned']
#
# def test_ownable_mixin():
#
#     Asset._instances.clear()
#
#     # Create some nodes and assets
#     trader1 = OwnerNode(label="trader1")
#     trader2 = OwnerNode(label="trader2")
#     asset1 = Asset(label="asset1", text="Golden Sword")
#     asset2 = Asset(label="asset2", text="Mystic Shield")
#
#     # Add assets to the nodes
#     trader1.add_child(asset1)
#     trader2.add_child(asset2)
#
#     # Check that the nodes own the correct assets
#     assert asset1 in trader1.owned
#     assert asset2 in trader2.owned
#
#     trade_handler = DiscreteTransactionHandler()
#     # check trade ok
#     assert trade_handler.can_transact(trader1, asset2, asset1, trader2)
#
#     # perform the trade
#     trade_handler.transact(trader1, asset2, asset1, trader2)
#
#     # Check that the nodes now own the other's assets
#     assert asset1 not in trader1.owned
#     assert asset1 in trader2.owned
#     assert asset2 in trader1.owned
#     assert asset2 not in trader2.owned
#
