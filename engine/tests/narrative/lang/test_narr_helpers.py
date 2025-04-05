
from tangl.narrative.lang.helpers import oxford_join, adjective_to_adverb

def test_adjective_to_adverb():
    # Test cases
    assert(adjective_to_adverb("clever") == "cleverly")
    assert(adjective_to_adverb("happy") == "happily")
    assert(adjective_to_adverb("simple") == "simply")
    assert(adjective_to_adverb("good") == "well")
    assert(adjective_to_adverb("rough") == "roughly")
    assert(adjective_to_adverb("shivering") is None)


def test_oxford_join():
    v = []
    j = oxford_join(v)
    assert j == ""

    v = ["hello"]
    j = oxford_join(v)
    assert j == "hello"

    v = ["hello", "goodbye"]
    j = oxford_join(v)
    assert j == "hello and goodbye"

    v = ["hello", "goodbye", "hello again"]
    j = oxford_join(v)
    assert j == "hello, goodbye, and hello again"

# def test_plural():
#
#     tests = {
#         "fairy": "fairies",
#         "army": "armies",
#         "octopus": "octopodes"  # really?
#     }
#
#     for k, v in tests.items():
#         print(f"{k} -> {plural(k)}")
#         assert plural(k) == v

# def test_num2word():
#     tests = {
#         "one": "one",
#         "50": "fifty"
#     }
#     for k, v in tests.items():
#         print(f"{k} -> {num2word(k)}")
#     assert num2word(k) == v
