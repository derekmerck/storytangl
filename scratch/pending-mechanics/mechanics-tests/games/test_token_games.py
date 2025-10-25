from collections import Counter

import pytest

pytest.skip(allow_module_level=True)

from tangl.mechanics.games.token_games import Token


@pytest.mark.skip(reason="not implemented")
def test_tokens():

    print( Token._instances )

    wallet = Counter(red_pawn=3, blue_knight=2)

    print( TokenHandler.value_by_affiliation(wallet) )

    assert TokenHandler.total_value(wallet) == 9
    assert TokenHandler.dominant_affiliation(wallet) == "blue"

@pytest.mark.skip(reason="not implemented")
def test_enum_tokens():

    TOK_TYPES = enum.IntEnum("TOK_TYPES", ['ROCK', 'PAPER', 'SCISSORS'])

    ice = Token( label="ice", affiliation=TOK_TYPES.ROCK )
    fire = Token( label="fire", affiliation=TOK_TYPES.PAPER )
    wind = Token( label="wind", affiliation=TOK_TYPES.SCISSORS )
    print( ice, fire, wind )

    bag = Counter(
        ice=10,
        fire=20,
        wind=30
    )
    print( bag )
    assert bag.total() == 60
    assert TokenHandler.total_value(bag) == 60
    assert TokenHandler.dominant_affiliation(bag) == TOK_TYPES.SCISSORS

    stone = Token( label="stone", affiliation=TOK_TYPES.ROCK, value=3.0 )
    bag = Counter(
        stone=10,
        ice=10,
        fire=20,
        wind=30
    )
    print( bag )
    assert bag.total() == 70
    assert TokenHandler.total_value(bag) == 90
    assert TokenHandler.dominant_affiliation(bag) == TOK_TYPES.ROCK
