from uuid import UUID, uuid4
from tangl.utils.is_valid_uuid import is_valid_uuid

def test_uuid_validator():
    # Test the function with some examples
    test_str1 = "550e8400-e29b-41d4-a716-446655440000"
    test_str2 = "not-a-uuid"
    test_str3 = "550e8400e29b41d4a716446655440000"
    test_int = 1234

    assert [is_valid_uuid(test_str1), is_valid_uuid(test_str2), is_valid_uuid(test_str3), is_valid_uuid(test_int)] == [True, False, False, False]

    for _ in range(50):
        assert is_valid_uuid(str(uuid4()))
