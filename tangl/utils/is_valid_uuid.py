import re
from uuid import UUID, uuid4

def is_valid_uuid(str_to_test: str) -> bool:
    """
    Test if a given string has the shape of a UUID.

    Parameters:
    - str_to_test (str): The string to test

    Returns:
    - bool: True if the string has the shape of a UUID, False otherwise
    """
    if not isinstance(str_to_test, str):
        return False
    # Define the UUID pattern
    uuid_pattern = re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.I)
    return bool(uuid_pattern.fullmatch(str_to_test))
