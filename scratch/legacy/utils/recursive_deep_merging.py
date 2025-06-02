"""
Various strategies for recursive deep merging and setting.

Ultimately, it is easier to just use 'python-box' when necessary.
"""

from collections import ChainMap
from typing import Any

def get_nested_value(data, keys, default=None):
    """
    Recursively get a nested dictionary value by specifying a list of keys.

    :param data: The dictionary to search.
    :param keys: A list of keys or a dot-separated string of keys.
    :param default: The default value to return if any key is not found.
    :return: The value from the nested dictionary or the default value.
    """

    if isinstance(keys, str):
        keys = keys.split('.')

    if not isinstance(keys, list):
        return default
    if not isinstance(data, dict):
        return default

    assert keys, "keys list must contain at least one element"

    key = keys[0]
    if len(keys) == 1:
        return data.get(key, default)

    if key in data:
        return get_nested_value(data[key], keys[1:], default)
    else:
        return default


class RecursiveChainMap(ChainMap):

    def get_by_path(self, path):
        """
        Retrieve a value using a dot-separated path, merging maps recursively.

        This "deep merges" dictionary kv entries.

        Example usage:

        >>> config1 = {'key1': {'key2': {'key3': 'value1', 'anotherKey': 'overWrittenValue'}}}
        >>> config2 = {'key1': {'key2': {'key3': 'value2', 'anotherKey': 'anotherValue'}}}
        >>> config3 = {'key1': {'key2': {'key3': 'value3'}}}
        >>> rcm = RecursiveChainMap(config3, config2, config1)
        >>> rcm.get_by_path('key1.key2.key3')
        'value3'
        >>> rcm.get_by_path('key1.key2.anotherKey')
        'anotherValue'
        """
        keys = path.split('.')
        current_level = self

        for key in keys:
            next_level = []
            # Collect the corresponding entries from all maps in the current chain
            for mapping in current_level.maps:
                if key in mapping:
                    value = mapping[key]
                    if isinstance(value, dict):
                        next_level.append(mapping[key])
                    else:
                        return value

            if not next_level:
                return None  # Or raise an exception if a key is missing

            # Create a new ChainMap for the next level
            current_level = RecursiveChainMap(*next_level)

        # At the final key, current_level contains the merged result of the deepest key
        return current_level


class DereferencingDict(dict[str, Any]):
    """
    Example:

    >>> ddict = DereferencingDict()
    >>> ddict['a'] = 'value'
    >>> ddict['b'] = '$a'
    >>> ddict['b']
    'value'
    """

    def __setitem__(self, key, value):
        if isinstance(value, str) and value.startswith('$'):
            reference_key = value[1:]
            if reference_key in self:
                value = self[reference_key]
        return super().__setitem__(key, value)
