from pprint import pprint

import yaml

from tangl.story.asset import Commodity
from tangl.world.games.incremental import Generator, IncrementalGame, IncrementalPlayer
# from tangl.story import ResourceManagerChallenge

import pytest

# language=YAML
commodity_descs_ = """
---
uid: labor
locals:
  ephemeral: True
---
uid: materials
---
uid: prestige
"""

# language=YAML
gen_descs_ = """
---
uid: font

cost:
  cash: 1.0
premium: 0.05

produces:
  labor: 5.0
---
uid: factory

cost: 
  cash: 1.0
premium: 1.05

consumes:
  labor: 1.0
produces:
  cash: 1.0
"""


@pytest.mark.skip( reason="Unimplemented")
def test_res_mgr():

    commodity_descs = yaml.safe_load_all(commodity_descs_)

    for desc in commodity_descs:
        asset = Commodity( **desc )

    Generator.__init_entity_subclass__()

    gen_descs = yaml.safe_load_all(gen_descs_)

    for desc in gen_descs:
        gen = Generator( **desc )

    print( Commodity._instances )
    print( Generator._instances )

    game = IncrementalGame( resources={ "font": 1, 'labor': 1.0, 'cash': 1.0 } )
    pprint( game )
    game.next_turn()
    pprint( game )

    game.buy_gen( "factory" )
    pprint( game )
    game.next_turn()
    pprint( game )

    # todo: need "show if inactive" for these actions


# language=yaml
rmc_desc_ = """
uid: mgr
label: Resource Manager UI
resources:  
  # commodities
  labor: 1
  materials: 1
  cash: 2
  # generators
  font: 1
  factory: 1

# discount: {}
# productivity_boost: {}
# efficiency_boost: {}

desc: |
  Manage your resources here.

actions:
  - label: Buy Font
    conditions:
      - resources >= next_cost('font')
    effects:
      - resources -= next_cost('font')
      - resources['font'] += 1

  - label: Font Productivity
    conditions: 
      - "resources >= { 'cash': 1 }"
    effects:
      - "resources['res1'] -= { 'cash': 1 }"
      - efficiency_boost['font'] += 0.5

  - label: Next tic
    # next: mgr

"""

@pytest.mark.skip( reason="unimplemented")
def test_res_mgr_ch():

    rmc_desc = yaml.safe_load( rmc_desc_ )
    blk = ResourceManagerBlock( **rmc_desc )

    pprint( blk.render() )


if __name__ == "__main__":
    test_res_mgr()
    test_res_mgr_ch()