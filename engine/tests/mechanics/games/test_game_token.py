from collections import Counter
import pytest

pytest.skip(allow_module_level=True)

from tangl.mechanics.games.simple_games.rps_game import RpsGameHandler, RpsMove
from tangl.mechanics.games.token_games.game_token import TokenHandler
from tangl.mechanics.games.token_games.token_game import RpsGameToken

Mv = RpsMove

paper_ = {
    'label': 'paper',
    'affiliation': Mv.PAPER,
    'value': 0.25,
    'text': 'The lightest of rps'
}

rock_ = {
    'label': 'rock',
    'affiliation': Mv.ROCK,
    'value': 1.0,
    'text': "The heaviest of rps"
}

def test_units():

    RpsGameToken(**paper_)
    RpsGameToken(**rock_)

    print( RpsGameToken.get_instance("paper") )
    print( RpsGameToken.get_instance("rock") )

    papers = Counter(paper=8)

    assert TokenHandler.dominant_affiliation(papers, RpsGameToken) is Mv.PAPER
    assert TokenHandler.total_value(papers, RpsGameToken) == 2.0

    rocks = Counter(rock=2)

    assert TokenHandler.dominant_affiliation(rocks, RpsGameToken) is Mv.ROCK
    assert TokenHandler.total_value(rocks, RpsGameToken) == 2.0
