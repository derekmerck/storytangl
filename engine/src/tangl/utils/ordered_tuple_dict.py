from typing import Any, Self, Union
import json
from collections import OrderedDict


class OrderedTupleDict(OrderedDict[str, tuple]):

    def __setitem__(self, key: str, value: Union[Any, tuple]) -> None:
        """Set an item, ensuring the value is a tuple."""
        if not isinstance(value, tuple):
            value = value,
        return super().__setitem__(key, value)

    def to_list(self) -> list[tuple]:
        """Convert to a list of tuples serialization."""
        return [(k, *v) for k, *v in super().items()]

    @classmethod
    def from_list(cls, data: list[tuple]) -> Self:
        """Create an OrderedTupleDict from a list of tuples."""
        return cls({k: tuple(v) for k, v in data})

    def to_json(self) -> str:
        """Convert to order-preserving JSON string."""
        return json.dumps(self.to_list())

    @classmethod
    def from_json(cls, data: str) -> Self:
        """Create an OrderedTupleDict from an order-preserving JSON string."""
        return cls.from_list(json.loads(data))

