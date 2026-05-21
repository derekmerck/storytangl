from tangl.journal.content import KvFragment as InfoFragment

#### TestKvFragment

def test_info_fragment_creation():
    fragment = InfoFragment(
        fragment_type="kv",
        content=[{"key": "score", "value": 100, "unit": "foo"}],
    )
    assert fragment.fragment_type == "kv"
    assert fragment.content[0].key == "score"
    assert fragment.content[0].value == 100
    assert fragment.content[0].unit == "foo"


# def test_kv_fragment_with_complex_value():
#     # Test with complex value
#     complex_value = {"points": 100, "level": 5, "achievements": ["gold", "silver"]}
#     fragment = KvFragment(
#         type="kv",
#         key="player_stats",
#         value=complex_value
#     )
#     assert fragment.content == complex_value
