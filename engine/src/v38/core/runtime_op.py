from typing import Any

from pydantic import BaseModel

from tangl.type_hints import StringMap
from tangl.utils.safe_builtins import safe_builtins

class RuntimeOp(BaseModel):
    """
    Generic runtime expression evaluator.

    This is the storage/serialization format for all runtime expressions.
    Use Query/Predicate/Effect subclasses for semantic clarity in domain code.

    RuntimeOp provides:
    - eval(ns) -> Any: Evaluate expression, return result
    - exec(ns) -> StringMap: Execute statement, return mutated namespace
    - satisfied_by(ns) -> bool: Evaluate as boolean condition
    - all_satisfied_by(*exprs, ns) -> bool: Evaluate all conditions are true
    - apply(ns) -> StringMap: Execute and return namespace (alias for exec)
    - apply_all(*exprs, ns) -> StringMap: Execute all exprs and return mutated namespace

    Examples:
        >>> RuntimeOp(expr="x + 5").eval({'x': 10})
        15
        >>> RuntimeOp(expr="x = 5").exec({'x': 10})
        {'x': 5}
        >>> RuntimeOp(expr="x > 5").satisfied_by({'x': 10})
        True
        >>> RuntimeOp.all_satisfied_by("abc + 1 == 124", "abc/3 == 41", ns={'abc': 123})
        True
        >>> RuntimeOp.apply_all("print(f'before: {abc}')", "abc = 456",
        ...                     "print(f'after: {abc}')", ns={'abc': 123})
        before: 123
        after: 456
        {'abc': 456}
    """
    expr: str

    @classmethod
    def _eval_expr(cls, s: str, ns: StringMap = None) -> Any:
        ns = ns or {}
        return eval(s, safe_builtins, ns)

    @classmethod
    def _exec_expr(cls, s: str, ns: StringMap = None) -> StringMap:
        ns = ns or {}
        exec(s, safe_builtins, ns)
        return ns

    def eval(self, ns: StringMap = None) -> Any:
        return self._eval_expr(self.expr, ns)

    def exec(self, ns: StringMap = None) -> StringMap:
        return self._exec_expr(self.expr, ns)

    def satisfied_by(self, ns: StringMap = None) -> bool:
        return bool(self.eval(ns))

    @classmethod
    def all_satisfied_by(cls, *exprs: str, ns: StringMap = None) -> Any:
        return all([bool(cls._eval_expr(e, ns)) for e in exprs])

    def apply(self, ns: StringMap = None) -> StringMap:
        return self._exec_expr(self.expr, ns)

    @classmethod
    def apply_all(cls, *exprs: str, ns: StringMap = None) -> StringMap:
        for e in exprs:
            cls._exec_expr(e, ns)
        return ns

# Hide some functionality in focused subclasses

class Query(RuntimeOp):
    """
    Read-only expression that computes a value.

    Use for:
    - Computed properties: max_health = Query("10 + level * 2")
    - Dynamic text: description = Query("f'You have {gold} gold'")
    - Formulas: damage = Query("strength * weapon_multiplier")

    Cannot mutate state (exec() raises TypeError).

    Examples:
        >>> health = Query(expr="base_health + vitality * 5")
        >>> health({'base_health': 100, 'vitality': 3})
        115
        >>> health.exec({'base_health': 100, 'vitality': 3}) # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        TypeError: Query cannot mutate state via exec()
    """

    def __call__(self, ns: StringMap = None) -> Any:
        return self.eval(ns)

    def exec(self, *_, **__) -> Any:
        """Predicates/Queries are read-only expressions."""
        raise TypeError(f"{self.__class__.__name__} cannot mutate state via exec()")

class Predicate(RuntimeOp):
    """
    Boolean condition for guards and requirements.

    Use for:
    - Availability checks: avail_if=[Predicate("key in inv")]
    - Requirements: requires=[Predicate("level >= 5")]
    - Conditional logic: if Predicate("health < 20")(state): ...

    Always returns bool. Cannot mutate state (exec() raises TypeError).

    Examples:
        >>> can_enter = Predicate(expr="'key' in inventory")
        >>> can_enter({'inventory': ['key', 'sword']})
        True
        >>> can_enter({'inventory': ['sword']})
        False
        >>> can_enter.exec({'inventory': ['sword']})
        Traceback (most recent call last):
          ...
        TypeError: Predicate cannot mutate state via exec()
    """

    def __call__(self, ns: StringMap = None) -> bool:
        return self.satisfied_by(ns)

    def exec(self, *_, **__) -> Any:
        """Predicates/Queries are read-only expressions."""
        raise TypeError(f"{self.__class__.__name__} cannot mutate state via exec()")

class Effect(RuntimeOp):
    """
    Imperative statement that mutates state.

    Use for:
    - Action consequences: effects=[Effect("inventory.append('key')")]
    - State updates: on_death=[Effect("player.health = 0")]
    - Side effects: Effect("log.append('Door unlocked')")

    Mutates namespace in place. Cannot evaluate for value (eval() raises TypeError).

    Example:
        >>> pickup = Effect(expr="inventory.append('key')")
        >>> ns = {'inventory': []}
        >>> pickup(ns)
        {'inventory': ['key']}
        >>> pickup.eval({'inventory': []})
        Traceback (most recent call last):
          ...
        TypeError: Effect cannot be evaluated for a value
    """

    def __call__(self, ns: StringMap = None) -> Any:
        return self.apply(ns)

    def eval(self, *_, **__) -> Any:
        """Effects are imperative statements."""
        raise TypeError(f"{self.__class__.__name__} cannot be evaluated for a value")
