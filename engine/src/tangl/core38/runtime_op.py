# tangl/core/runtime_op.py
"""Portable runtime expression wrappers for query, predicate, and effect operations.

The runtime-op family is intentionally small and serializable:

- :class:`RuntimeOp` stores the expression string and exposes eval/exec helpers.
- :class:`Query` is read-only value computation.
- :class:`Predicate` is read-only boolean computation.
- :class:`Effect` is write-oriented namespace mutation.

Notes
-----
Execution uses ``safe_builtins`` rather than full Python builtins.

Pass ``rand=Random(...)`` to inject a deterministic RNG into expression globals.
"""

from __future__ import annotations
from random import Random
from typing import Any

from pydantic import BaseModel

from tangl.type_hints import StringMap
from tangl.utils.safe_builtins import safe_builtins

class RuntimeOp(BaseModel):
    """
    Generic runtime expression evaluator.

    This is the storage/serialization format for portable runtime expressions.
    Use Query/Predicate/Effect subclasses for semantic clarity in domain code.

    RuntimeOp provides:
    - eval(ns, *, rand=None) -> Any: Evaluate expression, return result
    - exec(ns, *, rand=None) -> StringMap: Execute statement, return mutated namespace
    - satisfied_by(ns, *, rand=None) -> bool: Evaluate as boolean condition
    - all_satisfied_by(*exprs, ns, rand=None) -> bool: Evaluate all conditions are true
    - apply(ns, *, rand=None) -> StringMap: Execute and return namespace (alias for exec)
    - apply_all(*exprs, ns) -> StringMap: Execute all exprs and return mutated namespace

    Example:
        >>> RuntimeOp(expr="x + 5").eval({'x': 10})
        15
        >>> RuntimeOp(expr="x = 5").exec({'x': 10})
        {'x': 5}
        >>> RuntimeOp(expr="x > 5").satisfied_by({'x': 10})
        True
        >>> RuntimeOp.all_satisfied_by("abc + 1 == 124", "abc/3 == 41", ns={'abc': 123})
        True
        >>> RuntimeOp.apply_all("abc = abc + 1", "abc = abc * 2", ns={"abc": 123})
        {'abc': 248}
    """
    expr: str

    @classmethod
    def _eval_expr(
        cls,
        s: str,
        ns: StringMap = None,
        *,
        extra_globals: dict[str, Any] | None = None,
    ) -> Any:
        if ns is None:
            ns = {}
        globs: dict[str, Any] = {"__builtins__": safe_builtins}
        if extra_globals:
            sanitized_globals = {
                key: value
                for key, value in extra_globals.items()
                if key != "__builtins__"
            }
            globs.update(sanitized_globals)
        return eval(s, globs, ns)

    @classmethod
    def _exec_expr(
        cls,
        s: str,
        ns: StringMap = None,
        *,
        extra_globals: dict[str, Any] | None = None,
    ) -> StringMap:
        if ns is None:
            ns = {}
        globs: dict[str, Any] = {"__builtins__": safe_builtins}
        if extra_globals:
            sanitized_globals = {
                key: value
                for key, value in extra_globals.items()
                if key != "__builtins__"
            }
            globs.update(sanitized_globals)
        exec(s, globs, ns)
        return ns

    def eval(self, ns: StringMap = None, *, rand: Random | None = None) -> Any:
        """Evaluate this expression and return the result."""
        extra = {"rand": rand} if rand is not None else None
        return self._eval_expr(self.expr, ns, extra_globals=extra)

    def exec(self, ns: StringMap = None, *, rand: Random | None = None) -> StringMap:
        """Execute this statement and return the mutated namespace."""
        extra = {"rand": rand} if rand is not None else None
        return self._exec_expr(self.expr, ns, extra_globals=extra)

    def satisfied_by(self, ns: StringMap = None, *, rand: Random | None = None) -> bool:
        """Evaluate this expression as a truthy/falsey guard."""
        return bool(self.eval(ns, rand=rand))

    @classmethod
    def all_satisfied_by(
        cls,
        *exprs: str,
        ns: StringMap = None,
        rand: Random | None = None,
    ) -> bool:
        """Return ``True`` when all expressions evaluate truthy in the same namespace."""
        extra = {"rand": rand} if rand is not None else None
        return all(bool(cls._eval_expr(e, ns, extra_globals=extra)) for e in exprs)

    def apply(self, ns: StringMap = None, *, rand: Random | None = None) -> StringMap:
        """Alias of :meth:`exec` for effect-oriented call sites."""
        return self.exec(ns, rand=rand)

    @classmethod
    def apply_all(cls, *exprs: str, ns: StringMap = None) -> StringMap:
        """Execute expressions sequentially against one shared namespace."""
        if ns is None:
            ns = {}
        # want to use a _shared_ default ns for mutation, otherwise default is per call
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

    Example:
        >>> health = Query(expr="base_health + vitality * 5")
        >>> health({'base_health': 100, 'vitality': 3})
        115
        >>> health.exec({'base_health': 100, 'vitality': 3}) # doctest: +ELLIPSIS
        Traceback (most recent call last):
          ...
        TypeError: Query cannot mutate state via exec()
    """

    def __call__(self, ns: StringMap = None, *, rand: Random | None = None) -> Any:
        return self.eval(ns, rand=rand)

    @classmethod
    def _exec_expr(cls, *_, **__) -> Any:
        """Predicates/Queries are read-only expressions."""
        raise TypeError(f"{cls.__name__} cannot mutate state via exec()")

class Predicate(RuntimeOp):
    """
    Boolean condition for guards and requirements.

    Use for:
    - Availability checks: avail_if=[Predicate("key in inv")]
    - Requirements: requires=[Predicate("level >= 5")]
    - Conditional logic: if Predicate("health < 20")(state): ...

    Always returns bool. Cannot mutate state (exec() raises TypeError).

    Example:
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

    def __call__(self, ns: StringMap = None, *, rand: Random | None = None) -> bool:
        return self.satisfied_by(ns, rand=rand)

    @classmethod
    def _exec_expr(cls, *_, **__) -> Any:
        """Predicates/Queries are read-only expressions."""
        raise TypeError(f"{cls.__name__} cannot mutate state via exec()")

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

    def __call__(self, ns: StringMap = None, *, rand: Random | None = None) -> Any:
        return self.apply(ns, rand=rand)

    @classmethod
    def _eval_expr(cls, *_, **__) -> Any:
        """Effects are imperative statements."""
        raise TypeError(f"{cls.__name__} cannot be evaluated for a value")
