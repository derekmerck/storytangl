import pytest

from tangl.journal.fragment import KvFragment

pytest.skip(allow_module_level=True)

#### TestKvFragment

def test_kv_fragment_creation():
    # Test KV fragment with different value types
    fragment = KvFragment(
        type="kv",
        key="score",
        value=100
    )
    assert fragment.fragment_type == "kv"
    assert fragment.label == "score"
    assert fragment.content == 100

def test_kv_fragment_with_complex_value():
    # Test with complex value
    complex_value = {"points": 100, "level": 5, "achievements": ["gold", "silver"]}
    fragment = KvFragment(
        type="kv",
        key="player_stats",
        value=complex_value
    )
    assert fragment.content == complex_value
