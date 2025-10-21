# /tangl/core/dispatch/behavior.py
"""Behavior - dispatch version 37.2"""
from __future__ import annotations
from enum import IntEnum
from typing import Type, Callable, TypeVar, Generic, Optional
from functools import total_ordering
import inspect
import weakref

from pydantic import field_validator, model_validator, ConfigDict

from tangl.type_hints import StringMap
from tangl.utils.base_model_plus import HasSeq
from tangl.utils.func_info import FuncInfo, HandlerFunc
from tangl.core import Entity, Registry
from tangl.core.entity import Selectable, is_identifier
from .call_receipt import CallReceipt

# ----------------------------
# Kind Enums

class HandlerLayer(IntEnum):
    # Reverse sort inline > global
    INLINE = 1       # injected for task (ignore missing @task)
    LOCAL = 2        # defined on a node, ancestors, or graph
    AUTHOR = 3       # world mixins
    APPLICATION = 4  # included by application (i.e., vm jobs)
    GLOBAL = 5       # available everywhere (i.e., core jobs)

class HandlerPriority(IntEnum):
    """
    Execution priorities for handlers.

    Each Behavior is assigned a priority to control high-level ordering.
    The pipeline sorts handlers by these priorities first, with the
    following semantics:

    - :attr:`FIRST` (0) – Runs before all other handlers.
    - :attr:`EARLY` (25) – Runs after FIRST, but before NORMAL.
    - :attr:`NORMAL` (50) – Default middle priority.
    - :attr:`LATE` (75) – Runs after NORMAL, before LAST.
    - :attr:`LAST` (100) – Runs very last in the sequence.

    Users are also free to use any int as a priority. Values lower than 0 will
    run before FIRST, greater than 100 will run after LAST, and other values will
    sort as expected.
    """
    FIRST = 0
    EARLY = 25
    NORMAL = 50
    LATE = 75
    LAST = 100

class HandlerType(IntEnum):
    # Most specific
    INSTANCE_ON_CALLER = 5  # unbound def on caller class, we bind to runtime caller
    CLASS_ON_CALLER = 4     # classmethod on caller.__class__
    INSTANCE_ON_OWNER = 3   # bound to some manager instance (weakref)
    CLASS_ON_OWNER = 2      # classmethod on foreign manager class
    STATIC = 1              # unbound free function, signature (caller, *args, **kwargs)
    # Most general

# ----------------------------
# Utils

def _mro_dist(this_cls: Type, super_cls: Type) -> int:
    if super_cls is None:
        return 1 << 20  # "very far" when no constraint
    if not isinstance(this_cls, type) or not isinstance(super_cls, type):
        return 1 << 20
    mro = this_cls.mro()
    return mro.index(super_cls) if super_cls in mro else 1 << 20

# ----------------------------
# Behavior

OT = TypeVar("OT", bound=Entity)
CT = TypeVar("CT", bound=Entity)

@total_ordering
class Behavior(Entity, Selectable, HasSeq, Generic[OT, CT]):

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    # arbitrary types allowed for possible WeakRef owner
    func: HandlerFunc

    def has_func_name(self, value: str) -> bool:
        # for matching
        return self.func.__name__ == value

    @is_identifier
    def get_label(self) -> str:
        return self.label or self.func.__name__

    # classification is inferred in _populate_from_funcinfo unless explicitly provided
    handler_type: HandlerType
    caller_cls: Type[CT] = None   # for selection and dist; can infer on bind/call
    owner: OT | weakref.ReferenceType[OT] | None = None
    owner_cls: Type[OT] = None

    @model_validator(mode="before")
    @classmethod
    def _populate_from_funcinfo(cls, values: dict):
        """
        Hydrate Behavior from FuncInfo in one deterministic pass.
        Explicit kwargs win; inferred values fill gaps.
        Also normalizes a bound caller method (self, no 'caller') to unbound
        to avoid double-binding at call time.
        """
        func = values.get("func")
        if func is None:
            return values

        # Track explicit hints (before inference)
        explicit_handler_type = values.get("handler_type") not in (None, HandlerType.STATIC)
        explicit_owner = values.get("owner") is not None
        explicit_caller_cls = values.get("caller_cls") is not None

        owner_val = values.get("owner")
        owner_cls_hint = owner_val if isinstance(owner_val, type) else None
        owner_inst_hint = owner_val if (owner_val is not None and not isinstance(owner_val, type)) else None

        info = FuncInfo.from_func(
            func=func,
            handler_type=values.get("handler_type"),
            caller_cls=values.get("caller_cls"),
            owner_cls=owner_cls_hint,
            owner=owner_inst_hint,
        )
        if info is None:
            return values

        # Always use normalized func from FuncInfo (may unbind bound methods)
        values["func"] = info.func

        # handler_type: explicit wins, otherwise inferred
        if not explicit_handler_type:
            values["handler_type"] = info.handler_type

        # caller_cls: fill if missing
        if not explicit_caller_cls and getattr(info, "caller_cls", None) is not None:
            values["caller_cls"] = info.caller_cls

        # owner / owner_cls merging:
        # - If owner was NOT explicit: use FuncInfo to fill both owner and owner_cls as appropriate.
        # - If owner WAS explicit: keep the given owner, but still backfill owner_cls if missing.
        if not explicit_owner:
            if info.handler_type == HandlerType.INSTANCE_ON_OWNER:
                # Backfill owner_cls even for unbound manager methods; set owner if available
                if getattr(info, "owner_cls", None) is not None:
                    values["owner_cls"] = info.owner_cls
                if getattr(info, "owner", None) is not None:
                    values["owner"] = info.owner
            elif info.handler_type == HandlerType.CLASS_ON_OWNER:
                if getattr(info, "owner_cls", None) is not None:
                    values["owner_cls"] = info.owner_cls
        else:
            # explicit owner provided; ensure owner_cls is populated if missing
            if values.get("owner_cls") is None:
                if isinstance(owner_val, Entity):
                    values["owner_cls"] = owner_val.__class__
                elif isinstance(owner_val, type):
                    values["owner_cls"] = owner_val
                elif getattr(info, "owner_cls", None) is not None:
                    values["owner_cls"] = info.owner_cls

        return values

    # req if INST_ON_OWNER or CLASS_ON_OWNER
    @field_validator("owner", mode="before")
    @classmethod
    def _owner_to_weakref(cls, data):
        if isinstance(data, Entity):
            data = weakref.ref(data)
            # can guarantee that this is INST_ON_OWNER now
        # Classes and None pass through
        return data

    def mro_dist(self, caller: Entity = None) -> int:
        if caller is None:
            return -1
        return _mro_dist(caller.__class__, self.caller_cls)

    priority: HandlerPriority | int = HandlerPriority.NORMAL

    # todo: we used to have a 'registry aware' object type that knew
    #       to self-register.  Moved it to GraphItem, maybe should re-generalize?
    origin: Registry = None

    def origin_dist(self) -> int:
        # how far away is this behavior's origin from the caller by discovery
        # -1 = inline
        #  0 = self layer
        #  1-n = ancestor layers
        #  >n = APP, GLOBAL handler layers
        #  large = missing from registry
        # todo: still not sure this is right, what about a global handler
        #       referenced by a parent?
        if self.origin is None or self.handler_layer() is HandlerLayer.INLINE:
            return -1
        from tangl.core.registry import _CHAINED_REGISTRIES
        registries = _CHAINED_REGISTRIES.get()
        if registries is None or self.origin not in registries:
            # Called for a sort key without having a relevant chained registry ctx var
            return 1 << 20
        return registries.index(self.origin)

    def handler_layer(self) -> HandlerLayer:
        # this isn't really the discovery 'origin', it's the registry's layer in this case
        if self.origin is not None and self.origin.handler_layer is not None:
            return self.origin.handler_layer
        return HandlerLayer.INLINE

    task: Optional[str] = None   # "@validate", "@render", etc.

    def has_task(self, task: str) -> bool:
        # when filtered by behavior.matches(has_task=x)
        if task is None:
            # No task given, always match
            return True
        if self.handler_layer() is HandlerLayer.INLINE:
            # I may not have a task, but I am inline, loose handlers will _always_ match
            return True
        if self.task is not None and self.task == task:
            # I might match some non-None task
            return True
        if self.origin is not None and self.origin.task is not None and self.origin.task == task:
            # I might inherit my origin's non-None task
            return True
        return False

    def get_selection_criteria(self) -> StringMap:
        criteria = dict(self.selection_criteria)
        # We will get the registries task and caller_cls if any from the registry criteria merge
        if self.caller_cls is not None:
            criteria.setdefault("is_instance", self.caller_cls)
        if self.origin is not None:
            # small chance that the registry might have a more specific criterion,
            # like a lower bound on caller_cls, but that seems like improper usage.
            criteria = self.origin.get_selection_criteria() | criteria  # clobber
        return criteria

    @classmethod
    def _criteria_specificity(cls, **criteria) -> tuple[int, int, int]:
        # 3-tuple in css: #identifiers, .class/pseudo classes, association tags
        id_specifier = 1 if 'has_identifier' in criteria else 0
        class_specifier = 1 if 'is_instance' in criteria else 0
        other_specifiers = len(criteria) - id_specifier - class_specifier
        return id_specifier, class_specifier, other_specifiers

    @property
    def specificity(self) -> tuple[int, int, int]:
        # does not include task, since that's not in specifier, but maybe useful to know if
        # this handler has a task, or if it's using its registry's default task
        return self._criteria_specificity(**self.get_selection_criteria())

    def sort_key(self, caller: CT = None, by_origin: bool = False):
        """
        -  priority early < late   # late can clobber
        - -origin dist             # closer registry can clobber (if chained)
        -  global < inline         # inline can clobber
        - -mro dist                # closer func def can clobber (needs caller)
        - *fewer selectors < more  # more selectors can clobber
        -  static < class < inst   # most specific (inst) can clobber
        -  early < late            # earlier runs before later (later can clobber)

        `by_origin` flag -> flips priority and origin dist/layer ~ origin dist !important
        This is critical for ensuring that ancestor order is preserved and values shadowed
        by layer, not by priority when accumulating a namespace.
        """
        if by_origin:
            # by priority within registry/layer
            return (-self.origin_dist(),        # closer ancestors > farther ancestors
                    -self.handler_layer(),      # inline > globals
                     self.priority,             # explicit
                    -self.mro_dist(caller),     # subclass meth > superclass meth
                    *self.specificity,          # match specificity
                     self.handler_type,         # instance > class > static
                     self.seq)                  # registration order

        # by priority first
        return ( self.priority,                 # explicit
                -self.origin_dist(),            # closer ancestors > farther ancestors
                -self.handler_layer(),          # inline > globals
                -self.mro_dist(caller),         # subclass meth > superclass meth
                *self.specificity,              # match specificity
                 self.handler_type,             # instance > class > static
                 self.seq)                      # registration order

    def __lt__(self, other: Behavior):
        return self.sort_key() < other.sort_key()

    def bind_func(self, caller: CT) -> Callable:
        """
        There are several possible signatures for a handler:
        - `f(self/caller, *, ctx, other = None, result = None )`, mro instance methods, static methods
        - `f(self/owner, caller, *, ctx, result = None )`, instance methods on other nodes
        - `f(cls, caller, *, ctx, other = None, result = None )`, cls methods (on any cls)
        """
        match self.handler_type:
            # The instance case is not actually necessary as we always include _caller_
            # as the first argument in the standard invocation
            # case HandlerType.INSTANCE_ON_CALLER:
            #     return self.func.__get__(caller, caller.__class__)  # bind to caller
            case HandlerType.STATIC | HandlerType.INSTANCE_ON_CALLER:
                return self.func

            # For class methods, we only need to know the owner class if it's _not_
            # the caller's class.  In general, perhaps we don't need to distinguish
            # them and we can just assume owner/owner_cls -> caller.__class__ during
            # init.  In that case, we don't need to pass in 'caller' and this can be
            # cached.
            case HandlerType.CLASS_ON_CALLER:
                return self.func.__get__(caller.__class__, type)   # bind to caller's class
            case HandlerType.CLASS_ON_OWNER:  # bind to foreign class, no owner inst
                if not isinstance(self.owner_cls, type):
                    raise RuntimeError(f"Expected 'owner' to be a class type for CLASS_ON_OWNER, got {type(self.owner_cls)}")
                return self.func.__get__(self.owner_cls, type)

            # This is the exception, when we need to grab a reference to a specific
            # manager instance where this behavior is registered, a function that
            # takes self, but is not the caller.
            case HandlerType.INSTANCE_ON_OWNER:
                owner_inst = self.owner() if self.owner else None
                if owner_inst is None:  # owner GC'd or otherwise missing
                    raise RuntimeError("Behavior owner is not defined")
                return self.func.__get__(owner_inst, owner_inst.__class__)

            case _:
                raise RuntimeError("Unknown call mode")

    def __call__(self, caller: CT, *args, ctx = None, **params) -> CallReceipt:
        # bind func, call func, wrap in receipt
        bound = self.bind_func(caller)
        result = bound(caller, *args, ctx=ctx, **params)
        return CallReceipt(
            behavior_id=self.uid,
            result=result,
            # could put a lambda here if we want deferred/lazy eval or iter dispatch
            ctx=ctx,
            args=args,
            params=params
        )

    def unstructure(self) -> StringMap:
        raise RuntimeError(f"Do _not_ try to serialize {self!r}; contains Callable, WeakRef.")

    def get_func_sig(self):
        return self._get_func_sig(self.func)

    @staticmethod
    def _get_func_sig(func):
        if func is None:
            raise ValueError("func cannot be None")
        while hasattr(func, '__func__'):
            # May be a wrapped object
            func = func.__func__
        return inspect.signature(func)

    def __hash__(self) -> int:
        # delegate hash, assuming each func can only correspond to a single handler
        return hash(self.func)
