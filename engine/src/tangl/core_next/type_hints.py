from typing import Mapping, Any, Callable

# ------------------------------------------------------------
# Predicates & helper aliases
# ------------------------------------------------------------
Context = Mapping[str, Any]
Predicate = Callable[[Context], bool]          # return True to run
