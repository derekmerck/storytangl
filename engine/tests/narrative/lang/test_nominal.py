import pytest
from tangl.narrative.lang.nominal import Nominal


def test_default_plural():

    socks = Nominal(nouns=['socks'])
    assert socks.plural

    dress = Nominal(nouns=['dress', 'frock'])
    assert dress.plural is False


@pytest.fixture
def pants():
    pants = Nominal(
        nouns=['pants', 'trousers'],
        plural=True,
        adjectives=['blue'],
        quantifiers=['pair of']
    )
    return pants


def test_direct_det(pants):
    for _ in range(20):
        assert pants.np() in {"pants", "trousers",
                              "blue pants", "blue trousers"}

def test_indefinite_det(pants):
    for _ in range(20):
        assert pants.idet() in {"a pair of pants", "some pants",
                                "a pair of trousers", "some trousers",
                                "a pair of blue pants", "some blue pants",
                                "a pair of blue trousers", "some blue trousers"}

def test_definite_det(pants):
    for _ in range(20):
        assert pants.ddet() in {"the pants", "the trousers",
                                "the blue pants", "the blue trousers",
                                "the pair of pants", "the pair of trousers",
                                "the pair of blue pants", "the pair of blue trousers"}

def test_possessive_det(pants):
    for _ in range(20):
        assert pants.ppdet() in {"his pants", "her pants",
                                 "his trousers", "her trousers",
                                 "his blue pants", "her blue pants",
                                 "his blue trousers", "her blue trousers",
                                 "his pair of pants", "her pair of pants",
                                 "his pair of trousers", "her pair of trousers",
                                 "his pair of blue pants", "her pair of blue pants",
                                 "his pair of blue trousers", "her pair of blue trousers"}

def test_demonstrative_det(pants):
    for _ in range(20):
        assert pants.demonstrative() in {"these pants", "these trousers",
                                         "these blue pants", "these blue trousers",
                                         "this pair of pants", "this pair of trousers",
                                         "this pair of blue pants", "this pair of blue trousers"}
