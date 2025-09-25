import pytest

from tangl.core.fragment import KvFragment
from tangl.utils.ordered_tuple_dict import OrderedTupleDict

#### TestKvFragment

def test_kv_fragment_creation():
    # Test KV fragment with different value types
    otd = OrderedTupleDict()
    otd['score'] = 100, 'foo'
    fragment = KvFragment(
        type="kv",
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
