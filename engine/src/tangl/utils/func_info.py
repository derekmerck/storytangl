"""
Function-introspection utilities for StoryTangl handler registration.

Goals:
- Classify a callable into a HandlerType without mutating the object.
- Infer caller_cls and owner/owner_cls robustly (decorators, partials, locals, lambdas).
- Keep logic deterministic and side-effect free at registration time.
"""
from __future__ import annotations
import inspect, functools
import gc, types, warnings
from typing import Type, get_type_hints, runtime_checkable, Protocol, Optional, Any, TypeVar
try:
    from typing import Self as TypingSelf  # py311+
except Exception:  # pragma: no cover
    from typing_extensions import Self as TypingSelf
from enum import IntEnum
from dataclasses import dataclass

CT = TypeVar("CT")
OT = TypeVar("OT")

# Note this is runtime_checkable so Pydantic will allow it as a type-hint.
# It is not actually validated, so this is purely organizational and the function
# call will actually admit any type *args as long as at least 1 arg or 'caller'
# is supplied.
@runtime_checkable
class HandlerFunc(Protocol):
    """Loose callable contract used during registration; runtime-checked only."""
    def __call__(self: TypingSelf, caller: CT, *args, ctx: Optional[Any] = None, **params: Any) -> Any: ...

class HandlerType(IntEnum):
    """Relative binding specificity used for precedence during dispatch."""
    # Most specific
    INSTANCE_ON_CALLER = 5  # unbound def on caller class, we bind to runtime caller
    CLASS_ON_CALLER = 4     # classmethod on caller.__class__
    INSTANCE_ON_OWNER = 3   # bound to some manager instance (weakref)
    CLASS_ON_OWNER = 2      # classmethod on foreign manager class
    STATIC = 1              # unbound free function, signature (caller, *args, **kwargs)
    # Most general

def _unwrap_callable(f):
    """Return the base function object by unwrapping decorators, partials, and descriptors."""
    f = inspect.unwrap(f)
    if isinstance(f, functools.partial):
        f = f.func
    # unwrap descriptors to their function object
    while hasattr(f, "__func__"):
        f = f.__func__
    return f

def _defining_cls_from_qualname(func):
    """Best-effort declaring class from module globals using func.__qualname__ (no locals support)."""
    mod = inspect.getmodule(func)
    if not mod or not hasattr(func, "__qualname__"):
        return None
    qn = func.__qualname__
    # strip nested function scopes
    qn = qn.split(".<locals>.")[0]
    parts = qn.split(".")
    if len(parts) >= 2:
        cls_name = parts[-2]
        return getattr(mod, cls_name, None)
    return None

def _best_effort_declaring_class(func):
    """
    Try harder to find the declaring class for local/inner defs and lambdas (name-mismatch safe).
    Uses referrers and stack locals; only called at registration time.
    """
    cls = _defining_cls_from_qualname(func)
    if cls is not None:
        return cls

    name = getattr(func, "__name__", None)
    if not name:
        return None

    # 1) Look for a class object that owns this function by identity.
    for obj in gc.get_referrers(func):
        if isinstance(obj, type):
            try:
                dct = getattr(obj, "__dict__", None)
                if dct and any(v is func for v in dct.values()):
                    return obj
            except Exception:
                pass
        elif isinstance(obj, types.MappingProxyType):
            for maybe_cls in gc.get_referrers(obj):
                if isinstance(maybe_cls, type):
                    try:
                        dct2 = getattr(maybe_cls, "__dict__", None)
                        if dct2 and any(v is func for v in dct2.values()):
                            return maybe_cls
                    except Exception:
                        pass

    # 2) Scan up the call stack for locals holding the class (for <locals> cases).
    qn = getattr(func, "__qualname__", "")
    if ".<locals>." in qn:
        tail = qn.split(".<locals>.")[-1]
        parts = tail.split(".")
        # Expect "...<locals>.ClassName.func"; if no class token (e.g., "<lambda>"),
        # we cannot resolve a declaring class from the qualname alone.
        if len(parts) >= 2:
            try_class = parts[-2]
            for frameinfo in inspect.stack():
                locs = frameinfo.frame.f_locals
                cand = locs.get(try_class)
                if isinstance(cand, type):
                    dct3 = getattr(cand, "__dict__", None)
                    if dct3 and any(v is func for v in dct3.values()):
                        return cand
        # else: no class token present; fall through to None

    return None


def _get_type_hints_safe(func):
    """Get evaluated type hints, swallowing resolution errors."""
    try:
        return get_type_hints(
            func,
            globalns=getattr(inspect.getmodule(func), "__dict__", {}),
            include_extras=True,
        )
    except Exception:
        return {}

def _debug_func(f):
    """Lightweight inspector useful in tests; returns a dict of key binding facts."""
    f_unwrapped = _unwrap_callable(f)
    decl_cls = _defining_cls_from_qualname(f_unwrapped) or _best_effort_declaring_class(f_unwrapped)
    bound_self = getattr(f, "__self__", None)
    sig = inspect.signature(f_unwrapped)
    param_names = list(sig.parameters)
    hints = _get_type_hints_safe(f_unwrapped)
    return {
        "ismethod": inspect.ismethod(f),
        "__self__": bound_self,
        "bound_self_is_type": isinstance(bound_self, type) if bound_self is not None else None,
        "decl_cls": decl_cls,
        "decl_cls_name": getattr(decl_cls, "__name__", None),
        "params": param_names,
        "has_caller": "caller" in sig.parameters,
        "caller_hint": hints.get("caller"),
    }

# --------- Model ---------

@dataclass(frozen=True)
class FuncInfo:
    """Binding/typing info inferred for a handler callable.

    Attributes:
        func: The (possibly normalized) callable to register.
        handler_type: Classification of binding semantics (caller/owner/class/static).
        caller_cls: Inferred type expected for the 'caller' argument (or declaring class for INSTANCE_ON_CALLER).
        owner_cls: Inferred class of the owner (manager) when applicable.
        owner: Captured owner instance when applicable (may be None).
    """
    func: HandlerFunc
    handler_type: HandlerType
    caller_cls: Optional[Type]   # type of the 'caller' argument (or owner/decl class for instance-on-caller)
    owner_cls: Optional[Type]
    owner: Optional[Any] = None  # may be a strong ref; up to caller to weakref later if desired

    @classmethod
    def from_func(cls,
                  func: HandlerFunc,
                  handler_type: Optional[HandlerType] = None,
                  caller_cls: Optional[Type] = None,
                  owner_cls: Optional[Type] = None,
                  owner: Optional[Any] = None) -> Optional[TypingSelf]:
        """
        Analyze a callable and produce a FuncInfo with normalized metadata.

        Steps:
          1) Shape-first classification from signature (self/cls/caller), handling bound methods.
          2) Caller type inference from annotations; for 'self: Self', map to declaring class.
          3) Owner class inference only when an OWNER handler type is involved or explicitly provided.
          4) Refinement: explicit owner/owner_cls flips CALLER→OWNER variants.
          5) Diagnostics: warn when a functools.partial has positional args bound.

        Notes:
          - Local classes / class-body lambdas are supported via best-effort declaring-class recovery.
          - Accidentally bound caller methods are normalized to unbound to avoid double-binding.
        """
        if func is None:
            return None

        # Record explicit inputs before any inference
        explicit_handler_type = handler_type is not None
        explicit_owner = owner is not None
        explicit_owner_cls = owner_cls is not None
        explicit_caller_cls = caller_cls is not None
        exp_caller_cls = caller_cls

        # Unwrap descriptors/decorators/partials for analysis
        f_unwrapped = _unwrap_callable(func)

        # Declaring class (module-global first, then best-effort for locals)
        decl_cls = _defining_cls_from_qualname(f_unwrapped) or _best_effort_declaring_class(f_unwrapped)

        # Owner normalization: if an instance was provided, prefer its class
        if owner is not None and owner_cls is None:
            owner_cls = owner.__class__

        # Bound method detection
        bound_self = getattr(func, "__self__", None)
        is_bound_method = inspect.ismethod(func) and (bound_self is not None)

        # --- Signature analysis (shape) ---
        sig = inspect.signature(f_unwrapped)
        param_names = list(sig.parameters.keys())
        has_self_first = bool(param_names and param_names[0] == "self")
        has_cls_first  = bool(param_names and param_names[0] == "cls")
        has_caller     = "caller" in sig.parameters

        normalized_func = None  # if we need to unbind a caller method

        # === STEP 1: Primary handler_type inference (shape-first, no decl required) ===
        if not explicit_handler_type:
            if is_bound_method:
                if isinstance(bound_self, type):
                    handler_type = HandlerType.CLASS_ON_CALLER  # or CLASS_ON_OWNER
                    # owner_cls = bound_self
                elif has_self_first and has_caller:
                    # Manager instance method pattern
                    owner = owner or bound_self
                    owner_cls = owner_cls or bound_self.__class__
                    handler_type = HandlerType.INSTANCE_ON_OWNER
                elif has_self_first and not has_caller:
                    # Bound caller method; normalize to unbound
                    # normalize to N.v form; dispatcher will bind at call-time
                    normalized_func = f_unwrapped
                    func = normalized_func
                    handler_type = HandlerType.INSTANCE_ON_CALLER
                    owner = None  # caller methods don't use owner
                    caller_cls = type(bound_self)
                else:
                    handler_type = HandlerType.INSTANCE_ON_OWNER
                    owner = owner or bound_self
                    owner_cls = owner_cls or bound_self.__class__
            else:
                # Unbound function / lambda / local def
                if has_self_first and not has_caller:
                    handler_type = HandlerType.INSTANCE_ON_CALLER
                elif has_self_first and has_caller:
                    handler_type = HandlerType.INSTANCE_ON_OWNER
                elif has_cls_first:
                    handler_type = HandlerType.CLASS_ON_CALLER
                else:
                    handler_type = HandlerType.STATIC

        # === STEP 2: Caller class inference ===
        hints = _get_type_hints_safe(f_unwrapped)
        ann_caller = hints.get("caller")
        ann_self   = hints.get("self")

        if not explicit_caller_cls:
            if isinstance(ann_caller, type):
                caller_cls = ann_caller
            elif handler_type == HandlerType.INSTANCE_ON_CALLER:
                # self-method; use declaring class if we can find it
                caller_cls = decl_cls or caller_cls
                # Special case: self: Self — still maps to declaring class if available
                if caller_cls is None and ann_self is not None:
                    caller_cls = decl_cls

        # === STEP 3: OWNER class inference (only when needed) ===
        if not explicit_owner_cls:
            if handler_type in (HandlerType.INSTANCE_ON_OWNER, HandlerType.CLASS_ON_OWNER):
                owner_cls = owner_cls or decl_cls

        # === STEP 4: Consolidated refinement using explicitness and relationships ===
        # Flip based on explicit owner/owner_cls intent
        if (explicit_owner or explicit_owner_cls):
            if handler_type == HandlerType.CLASS_ON_CALLER:
                handler_type = HandlerType.CLASS_ON_OWNER
            elif handler_type == HandlerType.INSTANCE_ON_CALLER:
                handler_type = HandlerType.INSTANCE_ON_OWNER

        # Flip classmethod on foreign manager class if we can relate decl vs caller
        if handler_type == HandlerType.CLASS_ON_CALLER and decl_cls is not None and caller_cls is not None:
            if isinstance(decl_cls, type) and isinstance(caller_cls, type):
                # Only enforce foreign-owner flip when the caller type relationship is known
                if explicit_owner_cls and not issubclass(decl_cls, caller_cls):
                    handler_type = HandlerType.CLASS_ON_OWNER
                    owner_cls = owner_cls or decl_cls

        # Compatibility check for explicit caller_cls (compare explicit vs inferred)
        if explicit_caller_cls and ann_caller is not None and exp_caller_cls is not None:
            inferred_cls = ann_caller if isinstance(ann_caller, type) else (decl_cls if handler_type == HandlerType.INSTANCE_ON_CALLER else None)
            if not (issubclass(exp_caller_cls, inferred_cls) or issubclass(inferred_cls, exp_caller_cls)):
                raise RuntimeError("Incompatible caller_cls override")
        # If explicit was provided, keep it rather than any inferred value
        if explicit_caller_cls:
            caller_cls = exp_caller_cls

        # === STEP 5: Diagnostics for partials ===
        if isinstance(func, functools.partial) and func.args:
            warnings.warn(
                "Handler is a functools.partial with bound positional args; "
                "inference may be unreliable if 'caller' was pre-bound.",
                RuntimeWarning,
            )

        return cls(
            func=normalized_func or func,
            handler_type=handler_type,
            caller_cls=caller_cls,
            owner_cls=owner_cls,
            owner=owner,
        )

    @classmethod
    def debug_func(cls, func):
        return _debug_func(func)
