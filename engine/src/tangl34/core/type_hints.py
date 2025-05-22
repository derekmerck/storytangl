from typing import Any, NewType, Callable

# A dict with identifier-safe string keys
StringMap = NewType('StringMap', dict[str, Any])
# A string map of kwargs suitable for structuring an Entity, includes as 'obj_cls' and 'uid' key
UnstructuredData = NewType('UnstructuredData', dict[str, Any])
# An evaluable or executable expression within a context
Expr = str
# A function that takes a context and returns a boolean if the context satisfies the predicate
Predicate = Callable[[StringMap], bool]  # func(ctx) = bool
