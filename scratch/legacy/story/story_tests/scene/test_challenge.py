from pprint import pprint

import yaml
import pytest

from tangl.graph import Graph, GraphFactory
from tangl.story.scene import Block, Challenge

# language=YAML
data_ = """
---
label: rps_sample_challenge
obj_cls: Challenge

game:
  obj_cls: RpsGame
  scoring_n: 5
  # can provide any Game params, opponent strategy, etc...

player_move_descs:     # indexed by `player_move`
  rock:
    - You play rock.
    - You play stone.

opponent_move_descs:   # indexed by `opponent_move`
  rock:
    - She plays rock.
    - She plays stone

round_result_descs:  # indexed by `round_result`
  win:
    - |-
      You won with {{ player_move }} against {{ opponent_move }}.

      >> [!OPPONENT.sad]
      >> Hrmph. Lucky.

  lose: 
    - |-
      You tried {{ player_move }} but lost against {{ opponent_move }}.

      >> [!OPPONENT.happy]
      >> Hah, you can't beat me.

game_state_descs: 
  - >-
    The score is currently {{ player_score }} vs. {{ opponent_score }}.  
    It is round {{ game_round }} of {{ game_scoring_n }}.

opponent_cue_descs:  # indexed by `opponent_next_move`
  rock:
    - She is planning to play rock, you can beat her with paper.
  paper:
    - She is planning to play paper, you can beat her with scissors.
  scissors:
    - She is planning to play scissors, you can beat her with rock.


game_actions:
  # Map actions to game moves, takes any action params, conditions, effects etc
  - move: rock
    text: play rock
    icon: rock
  - move: paper
    text: play paper
    icon: paper
  - move: scissors
    text: play scissors
    icon: scissors
    
continues:
  # When the game is over, continue conditionally to the next node
  - conditions: [ player_won_game ]
    successor_ref: rps_sample_won
    
  - conditions: [ player_lost_game ]
    successor_ref: rps_sample_lost

---
label: rps_sample_won
obj_cls: Block
text: ## You won!

actions:
  - text: Try again
    effects: [ rps_sample_challenge.reset() ]
    successor_ref: rps_sample_challenge

---
label: rps_sample_lost
obj_cls: Block
text: ## You lost!

actions:
  - text: Try again
    effects: [ rps_sample_challenge.reset() ]
    successor_ref: rps_sample_challenge
"""
data = yaml.safe_load_all(data_)

@pytest.fixture
def graph() -> Graph:
    g = Graph()
    for d in data:
        GraphFactory().create_node(**d, graph=g)
    return g

def test_challenge_wrapper(graph):
    ch = graph.get_node('rps_sample_challenge')
    # print( ch )

    pprint( ch.player_move_descs )
    print( ch.player_move_descs.choice('rock') )

    r = ch.render()
    pprint( r )

    ns = ch.get_namespace()
    pprint( ns )


