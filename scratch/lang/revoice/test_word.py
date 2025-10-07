import pytest

from tangl.world.narrator.voice.word import QualifierList, OverlayWord

# fat = Word(
#     uid="fat",
#     **{"thin": ["thin"],
#        "fat": ["fat"],
#        '__': ["unknown"]}
# )
#
# she_is_fat = Phrase(
#     rex = "she is (fat|thin)",
#     semex = [{'pronoun', 'subj'}, {'verb', 'to be'}, {'adj', lambda x: x in ['fat', 'thin']}],
#     template = "{{ nom(PT.S, ref) }} {{ conj('to be', ref) }} {{ word('fat', ref) }}"
# )
#
# long_blonde_hair = Phrase(
#     # if you can identify ref
#     rex = "(long|short) (blond|brunette) hair",
#     # if tagged with voice
#     semex = [{'adj', ['long', 'short']}, {'adj', ['blonde', 'brunette'], {'noun', 'hair'}}],
#     template = "{{ word('hair_len', ref, 'hair' }} {{ word('hair_color', ref, 'hair') }} hair"
# )

@pytest.mark.skip()
def test_sememe():

    ref = QualifierList(["thin"])
    assert( fat(ref) == "thin" )

    ref = QualifierList(["fat"])
    assert( fat(ref) == "fat" )

    ref = QualifierList(["abc"])
    assert( fat(ref) == "unknown" )

    ref = QualifierList()
    assert( fat(ref) == "unknown" )

@pytest.mark.xfail(reason="Not implemented")
def test_private_sememe():

    fat2 = OverlayWord( uid='fat2', include=["fat"])

    ref = QualifierList(["thin"])
    assert( fat2(ref) == "thin" )

    ref = QualifierList(["fat"])
    assert( fat2(ref) == "fat" )

    fat2 = OverlayWord( uid='fat2', include=["fat"], exclude=["thin"], thin=["skinny"])

    ref = QualifierList(["thin"])
    assert( fat2(ref) == "skinny" )

    ref = QualifierList(["fat"])
    assert( fat2(ref) == "fat" )



# test_sememe()
# test_private_sememe()