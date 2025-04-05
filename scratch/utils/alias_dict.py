from uuid import UUID
from typing import Protocol, Callable, Iterable

class HasAliases(Protocol):

    uid: UUID
    def get_aliases(self) -> Iterable[str]: ...


class AliasDict(dict[UUID | str, HasAliases]):
    """
    This is a many-to-many mapping that tracks items by aliases and
    natively handles filter conditions.

    The key features are `add(item)`, which inserts a new item into the
    index, and `find_items(*aliases, filt)`, which searches the index
    for matching aliases and then filters the results.  If no aliases
    are submitted to 'find', it will return all items that pass the filter.

    `find_item` (singular) is a convenience function that returns only
    the first candidate from 'find_items' or raises an error if more than
    1 candidate was found.

    Inserted objects must have at least one of a `uid` field or a
    `get_aliases` instance method.
    """

    def add(self, value: HasAliases):
        """
        Index an object by 'uid', with optional 'get_aliases' function.
        If an object's aliases are updated, call this again to add or
        discard the updates.
        """
        aliases = set()
        if hasattr(value, 'uid'):
            aliases.add( value.uid )
        if hasattr(value, 'get_aliases'):
            aliases.update(value.get_aliases())
        if not aliases:
            raise TypeError('Item to add must have a uid or indicate aliases with `get_aliases()`')
        for alias in aliases:
            self[alias] = value

        stale_items = set()
        for k, v in self.items():
            if v is value and k not in aliases:
                stale_items.add(k)
        for k in stale_items:
            del self[k]

    def find_items(self, *aliases, filt: Callable = None) -> list[HasAliases]:
        """Find objects by a list of aliases, with an optional `filt` function"""
        if aliases:
            candidates = set( [ self[a] for a in aliases if a in self ] )
        else:
            candidates = self.values()
        if candidates and filt:
            candidates = filter( filt, candidates)
        if candidates:
            candidates = list(set(candidates))
            return candidates

    def find_item(self, *aliases, filt: Callable = None) -> HasAliases:
        """Convenience function that returns only the first match from `find_items`"""
        results = self.find_items(*aliases, filt = filt)
        if results:
            if len(results) > 1:
                raise KeyError(f"`find_items` did not return a unique result ({len(results)} candidates)")
            return results[0]
