"""
Function Signature Comparison for Hook Validation

This module provides a specialized function, `compare_ftypes`, designed to compare
the signatures of two callable objects (functions or methods) for compatibility
in the context of hook system validation.

The comparison is focused on a subset of signature elements, making it suitable
for hook systems where some flexibility is allowed, but core signature elements
must match.

What it checks:
1. Return type compatibility (if annotated)
2. Presence of **kwargs in both functions
3. Type compatibility of the first parameter (if annotated)
4. Number of required positional parameters (excluding self/cls and **kwargs)

What it ignores:
1. Names of parameters (except for the first one in methods)
2. Types of parameters other than the first one
3. Default values of parameters
4. Keyword-only parameters
5. Order of **kwargs (as long as it's present in both functions)

Usage:
    compare_ftypes(pattern_func, hook_func) -> bool

    Returns True if hook_func is compatible with pattern_func according to the
    criteria listed above, False otherwise.
"""
import logging
from typing import Callable, Any, get_type_hints
import inspect


logger = logging.getLogger(f"tangl.{__name__}")
logger.setLevel(logging.WARNING)


def is_subclass_or_same(sub, sup):
    logger.debug(f"Comparing {sub} and {sup}")
    if sub == sup or sup == Any or sub == Any:
        return True
    try:
        return issubclass(sub, sup)
    except TypeError:
        logger.debug(f"TypeError when comparing {sub} and {sup}")
        return False


def compare_ftypes(func1: Callable, func2: Callable) -> bool:
    logger.debug(f"Comparing {func1.__name__} and {func2.__name__}")

    # Get type hints for both functions
    try:
        hints1 = get_type_hints(func1)
        hints2 = get_type_hints(func2)
    except NameError as e:
        logger.debug(f"NameError when getting type hints: {e}")
        logger.debug("Falling back to Any for unresolved annotations")
        hints1 = {k: v if not isinstance(v, str) else Any for k, v in
                  get_type_hints(func1, include_extras=True).items()}
        hints2 = {k: v if not isinstance(v, str) else Any for k, v in
                  get_type_hints(func2, include_extras=True).items()}

    # Compare return types
    ret1 = hints1.get('return', inspect.Signature.empty)
    ret2 = hints2.get('return', inspect.Signature.empty)
    logger.debug(f"Return types - {ret1} and {ret2}")
    if ret1 != inspect.Signature.empty and ret2 != inspect.Signature.empty:
        if not is_subclass_or_same(ret2, ret1):
            logger.debug("Return type mismatch")
            return False

    # Get parameters
    sig1 = inspect.signature(func1)
    sig2 = inspect.signature(func2)
    params1 = list(sig1.parameters.values())
    params2 = list(sig2.parameters.values())

    # Check for **kwargs in both functions
    if not (params1 and params1[-1].kind == inspect.Parameter.VAR_KEYWORD and
            params2 and params2[-1].kind == inspect.Parameter.VAR_KEYWORD):
        logger.debug("kwargs mismatch")
        return False

    # Compare first argument types if annotated
    if params1 and params2:
        p1_name, p2_name = params1[0].name, params2[0].name
        p1_type = hints1.get(p1_name, inspect.Signature.empty)
        p2_type = hints2.get(p2_name, inspect.Signature.empty)
        logger.debug(f"First arg types - {p1_type} and {p2_type}")
        if p1_type != inspect.Signature.empty and p2_type != inspect.Signature.empty:
            if not is_subclass_or_same(p2_type, p1_type):
                logger.debug("First arg type mismatch")
                return False

    # Count required positional arguments (excluding self/cls and **kwargs)
    def count_required_args(params):
        return sum(1 for p in params[1:-1] if p.default == inspect.Parameter.empty and
                   p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD))

    required_args1 = count_required_args(params1)
    required_args2 = count_required_args(params2)
    logger.debug(f"Required args count - {required_args1} and {required_args2}")

    return required_args1 == required_args2
