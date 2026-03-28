import pytest

from tangl.media.stableforge.parse_info import parse_info

info = \
    'pretty aria the bard, purple lips, lavender eyes, long legs, ' \
    'ponytail hair, (((classical japanese ink brush and woodblock ' \
    'art scroll)))\n' \
    'Steps: 20, Sampler: Euler a, CFG scale: 7, Seed: 2286316612, ' \
    'Size: 512x512'

expected = {'prompt': 'pretty aria the bard, purple lips, lavender eyes, long legs, ponytail hair, (((classical japanese ink brush and woodblock art scroll)))', 'steps': 20, 'sampler': 'Euler a', 'cfg_scale': 7, 'seed': 2286316612, 'width': '512', 'height': '512'}


@pytest.fixture
def test_pair() -> tuple[str, dict]:
    return info, expected


def test_parse_info(test_pair):

    info, expected = test_pair

    data = parse_info(info)
    print( data )
    assert data == expected

