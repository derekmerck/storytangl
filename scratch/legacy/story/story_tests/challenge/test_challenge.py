
from pathlib import Path
from tangl.games.enums import Result
from pprint import pprint
import yaml

from tangl.story import Challenge, Scene

import pytest

# language=YAML
ch_ = """
uid: test_ch
label: Test Challenge

blocks:
  basic:
    block_cls: Challenge
    label: Test Basic
    continues:
      - conditions:
          - game_status is Result.WIN
        next: win
      - conditions:
          - game_status is Result.LOSE
        next: lose
        
  rps:
    block_cls: Challenge
    label: Test Rps
    game:
      game_cls: RpsGame
    continues:
      - conditions:
          - game_status is Result.WIN
        next: win
      - conditions:
          - game_status is Result.LOSE
        next: lose
    
  win:
    label: You won!
    
  lose:
    label: You lost!
"""

ch_spec = yaml.safe_load( ch_ )


def test_basic_ch():
    ch = Challenge( **ch_spec['blocks']['basic'] )
    print( ch )

    pprint( ch.render() )


def test_rps_ch():
    ch = Challenge( **ch_spec['blocks']['rps'] )
    print( ch )

    pprint( ch.render() )


def test_basic_ch_scene():
    ch = Scene( **ch_spec )
    print( ch )

    pprint( ch.blocks['basic'].render() )
    ch.blocks['basic'].actions[0].apply()
    print( "basic: ", ch.blocks['basic'].actions[0].follow().uid )
    pprint(ch.blocks['basic'].render() )


def test_rps_full_scene():

    here = Path( __file__ ).parent
    with open( here / "pu_game.yaml" ) as f:
        data = yaml.safe_load( f )

    from tangl.story import Scene
    sc = Scene( **data )

    print( sc )

    pprint( sc.blocks['start'].render() )
    ch = sc.blocks['start'].actions[0].follow()
    pprint( ch.render() )


if __name__ == "__main__":
    test_basic_ch()
    test_basic_ch_scene()
    test_rps_ch()
    pass
