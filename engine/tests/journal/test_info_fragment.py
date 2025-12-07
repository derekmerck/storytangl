import pytest

from tangl.journal.content import KvFragment as InfoFragment
from tangl.utils.ordered_tuple_dict import OrderedTupleDict

#### TestKvFragment

def test_info_fragment_creation():
    # Test KV fragment with different value types
    otd = OrderedTupleDict()
    otd['score'] = 100, 'foo'
    fragment = InfoFragment(
        fragment_type="kv",
        content=otd
    )
    assert fragment.fragment_type == "kv"
    assert fragment.content['score'] == (100, 'foo')


# def test_kv_fragment_with_complex_value():
#     # Test with complex value
#     complex_value = {"points": 100, "level": 5, "achievements": ["gold", "silver"]}
#     fragment = KvFragment(
#         type="kv",
#         key="player_stats",
#         value=complex_value
#     )
#     assert fragment.content == complex_value
