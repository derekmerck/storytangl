import pytest
from uuid import UUID
from pydantic import Field

from tangl.core.singleton import MutableSingleton


def test_basic_mutable_singleton():
    """Test basic mutable singleton functionality"""
    s1 = MutableSingleton(secret="test1")
    original_uid = s1.uid

    # Change secret
    s1.secret = "test2"
    assert s1.uid != original_uid

    # New instance with new secret should return same instance
    s2 = MutableSingleton(secret="test2")
    assert s1 is s2


def test_registry_management():
    """Test that registry is properly maintained when identity changes"""
    s = MutableSingleton(secret="test1")
    original_uid = s.uid

    # Should be registered under original uid
    assert MutableSingleton.has_instance(original_uid)
    assert len(MutableSingleton._instances) == 1

    # Change identity
    s.secret = "test2"
    new_uid = s.uid

    # Should now be registered under new uid only
    assert not MutableSingleton.has_instance(original_uid)
    assert MutableSingleton.has_instance(new_uid)
    assert len(MutableSingleton._instances) == 1


def test_identity_collisions():
    """Test handling of identity collisions"""
    s1 = MutableSingleton(secret="test1")
    s2 = MutableSingleton(secret="test2")

    # Trying to change s2's secret to match s1 should raise error
    with pytest.raises(KeyError):
        s2.secret = "test1"


class MetadataSingleton(MutableSingleton):
    test_data: str = None

def test_identity_independence():
    """Test that non-identity fields can be modified"""
    s = MetadataSingleton(secret="test")
    original_uid = s.uid

    # Modifying metadata shouldn't affect identity
    s.test_data = "value"
    assert s.uid == original_uid

    # Verify metadata was updated
    assert s.test_data == "value"


def test_invalid_secret():
    """Test handling of invalid secrets"""
    with pytest.raises(ValueError):
        MutableSingleton(secret="")

    with pytest.raises(ValueError):
        MutableSingleton(secret=None)


def test_reregistration():
    """Test that instance can return to previous identity"""
    s = MutableSingleton(secret="test1")
    original_uid = s.uid

    # Change identity
    s.secret = "test2"
    intermediate_uid = s.uid

    # Change back
    s.secret = "test1"
    final_uid = s.uid

    assert original_uid == final_uid
    assert intermediate_uid != final_uid
    assert MutableSingleton.has_instance(final_uid)
    assert not MutableSingleton.has_instance(intermediate_uid)


def test_concurrent_instances():
    """Test handling multiple instances with changing identities"""
    s1 = MutableSingleton(secret="test1")
    s2 = MutableSingleton(secret="test2")
    s3 = MutableSingleton(secret="test3")

    assert len(MutableSingleton._instances) == 3

    # Change identities in sequence
    s1.secret = "new1"
    s2.secret = "new2"
    s3.secret = "new3"

    assert len(MutableSingleton._instances) == 3
    assert len({s1.uid, s2.uid, s3.uid}) == 3  # All unique

# def test_identity_tracking():
#     """Test identity tracking property"""
#     s = MutableSingleton(secret="test")
#     original_identity = s.current_identity
#
#     s.secret = "new_secret"
#     new_identity = s.current_identity
#
#     assert original_identity != new_identity
#     assert "test" in original_identity
#     assert "new_secret" in new_identity

@pytest.mark.parametrize("secret,next_secret", [
    ("test", "test"),  # Same secret
    ("", "valid"),  # Empty to valid
    ("valid", ""),  # Valid to empty
    (None, "valid"),  # None to valid
])
def test_edge_cases(secret, next_secret):
    """Test various edge cases for secret changes"""
    if not secret:  # Should fail initialization
        with pytest.raises(ValueError):
            MutableSingleton(secret=secret)
        return

    s = MutableSingleton(secret=secret)

    if not next_secret:  # Should fail secret change
        with pytest.raises(ValueError):
            s.secret = next_secret
    else:
        s.secret = next_secret
        assert s.secret == next_secret

@pytest.fixture(autouse=True)
def cleanup():
    MutableSingleton.clear_instances()
    yield
    MutableSingleton.clear_instances()
