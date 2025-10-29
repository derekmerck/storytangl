# /tangl/core/dispatch/behavior.py
"""
Dispatch – Behavior model (v3.7.2)

This module defines :class:`Behavior` and related enums used by the
:class:`~tangl.core.dispatch.behavior_registry.BehaviorRegistry`.
Behaviors wrap callables (functions, instance methods, class methods)
and carry metadata for selection, ordering, and auditing.

Why
----
Unify all dispatchable routines behind a single, inspectable wrapper
that can be filtered and stably ordered across multiple registries
("inline → local → author → application → global"), while remaining
agnostic about how the underlying callable is defined (free function,
instance/class method, manager-owned method). The goal is deterministic,
testable pipelines with receipts for each invocation.

Key Features
------------
* **Flexible binding** — Binding is inferred from signature and hints
  (:class:`HandlerType`), so Behaviors can wrap free functions, owner
  instance methods, or class methods without boilerplate.
* **Layer-aware** — Behaviors remember which :class:`Registry` they came
  from; when registries are chained, origin distance and
  :class:`HandlerLayer` provide stable "CSS-like" precedence.
* **Prioritized & specific** — First sort by :class:`HandlerPriority`,
  then by origin, layer, MRO distance, selector specificity, handler type,
  and registration order.
* **Selectable** — Behaviors are :class:`~tangl.core.entity.Selectable`,
  exposing structured criteria (task, caller class, tags) used by
  :class:`BehaviorRegistry.dispatch`.
* **Audited** — Every call returns a :class:`CallReceipt`.

API
---
- :class:`Behavior` — wrapper with sorting/binding/selection helpers.
- :class:`HandlerPriority`, :class:`HandlerLayer`, :class:`HandlerType` —
  ordering, layering, and binding modes.
- :meth:`Behavior.sort_key` — stable ordering tuple (supports ``by_origin``).
- :meth:`Behavior.__call__` — invoke and receive a :class:`CallReceipt`.
- See :class:`BehaviorRegistry` for filtering and iteration
  (:meth:`dispatch`, :meth:`chain_dispatch`).
"""
from __future__ import annotations
from enum import IntEnum
from typing import Type, Callable, TypeVar, Generic, Optional
from functools import total_ordering
import inspect
import weakref
import logging

from pydantic import field_validator, model_validator, ConfigDict, Field

from tangl.type_hints import StringMap
from tangl.utils.enum_plus import EnumPlusMixin
from tangl.utils.base_model_plus import HasSeq
from tangl.utils.func_info import FuncInfo, HandlerFunc
from tangl.core import Entity, Registry
from tangl.core.entity import Selectable, is_identifier
from .call_receipt import CallReceipt

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# ----------------------------
# Kind Enums

class HandlerLayer(IntEnum):
    """
    Logical origin of a behavior used during chained registry sorting.

    Lower numeric values are considered more specific and sort earlier
    when combining registries:

    - :attr:`INLINE` (1) – behavior injected for a single task call.
    - :attr:`LOCAL` (2) – registered on the caller (node/graph) or its ancestors.
    - :attr:`AUTHOR` (3) – world/domain-provided mixins.
    - :attr:`APPLICATION` (4) – task domain provided behaviors (e.g., story, discourse).
    - :attr:`SYSTEM` (5) – system provided behaviors (e.g., vm, service, media).
    - :attr:`GLOBAL` (6) – core defaults available everywhere.
    """
    # Reverse sort inline > global
    INLINE = 1       # injected for task (ignore missing @task)
    LOCAL = 2        # defined on a node, ancestors, or graph
    AUTHOR = 3       # world mixins
    APPLICATION = 4  # included by application (i.e., story jobs)
    SYSTEM = 5       # subsystem jobs (i.e., vm jobs, service jobs)
    GLOBAL = 6       # available everywhere (i.e., core jobs)

class HandlerPriority(EnumPlusMixin, IntEnum):
    """
    Execution priorities for handlers.

    Each Behavior is assigned a priority to control high-level ordering.
    The pipeline sorts handlers by these priorities first, with the
    following semantics:

    - :attr:`FIRST` (0)   – Runs before all other handlers.
    - :attr:`EARLY` (25)  – Runs after FIRST, but before NORMAL.
    - :attr:`NORMAL` (50) – Default middle priority.
    - :attr:`LATE` (75)   – Runs after NORMAL, before LAST.
    - :attr:`LAST` (100)  – Runs very last in the sequence.

    Users are also free to use any int as a priority. Values lower than 0 will
    run before FIRST, greater than 100 will run after LAST, and other values will
    sort as expected.
    """
    FIRST = 0
    EARLY = 25
    NORMAL = 50
    LATE = 75
    LAST = 100

class HandlerType(EnumPlusMixin, IntEnum):
    """
    Binding mode inferred from the wrapped callable’s signature and hints.

    - :attr:`INSTANCE_ON_CALLER` – unbound instance method declared on the caller’s class;
      bound to the runtime caller at invocation.
    - :attr:`CLASS_ON_CALLER` – ``@classmethod`` defined on the caller’s class.
    - :attr:`INSTANCE_ON_OWNER` – unbound instance method defined on a *manager/owner*
      instance held via weakref; bound to that owner at invocation.
    - :attr:`CLASS_ON_OWNER` – ``@classmethod`` defined on a foreign manager/owner class.
    - :attr:`STATIC` – free function; receives ``caller`` as its first argument.

    The :meth:`Behavior.bind_func` helper uses this value to compute the bound callable.
    """
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
    """
    Behavior(func: ~typing.Callable[[Entity, ...], typing.Any], priority: int = NORMAL)

    Wrapper around a dispatchable callable with deterministic ordering,
    selection, and auditing. Behaviors can wrap free functions, instance
    methods, and class methods; binding is inferred and applied at call time.

    Why
    ----
    Provide a single abstraction for all dispatchable routines so the
    :class:`BehaviorRegistry` can filter, sort, and invoke them uniformly,
    even when they originate from different registries (inline/local/author/
    application/global). Each call yields a :class:`CallReceipt` for audit.

    Key Features
    ------------
    * **Flexible binding** – uses :class:`HandlerType` plus runtime hints to
      bind correctly to the caller, a foreign owner, or a class object.
    * **Prioritized & stable** – ordered by priority, origin distance,
      layer, MRO distance, selector specificity, handler type, and
      registration sequence.
    * **Selectable** – exposes criteria (e.g., ``task``, ``caller_cls``)
      merged with the origin registry’s criteria for CSS-like matching.
    * **Layer-aware** – remembers the :class:`Registry` of origin to compute
      chain order and shadowing during ``chain_dispatch``.
    * **Auditable** – invocation returns a :class:`CallReceipt` capturing
      parameters, context, and results.

    API
    ---
    - :meth:`__call__(caller, *args, ctx=None, **params) <__call__>` – bind,
      invoke, and return a :class:`CallReceipt`.
    - :meth:`bind_func` – resolve a bound callable from :attr:`handler_type`.
    - :meth:`sort_key` – stable tuple used by registries for ordering.
    - :meth:`get_selection_criteria` – behavior+registry criteria for matching.
    - :attr:`priority`, :attr:`handler_type`, :attr:`task`, :attr:`origin` –
      key metadata influencing selection and order.

    .. admonition:: Reserved Keywords

       ``ns`` and ``ctx`` are reserved keyword arguments on the called function
       signature. They may be added or manipulated during :meth:`__call__`.
    """
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
    def _populate_from_func_info(cls, values: dict):
        """
        Hydrate Behavior from FuncInfo in one deterministic pass.
        Explicit kwargs win; inferred values fill gaps.
        Also normalizes a bound caller method (self, no 'caller') to unbound
        to avoid double-binding at call time.
        """
        # todo: can't we merge _all_ of this into func info's preprocessor
        #       as hints?
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
    origin: Registry = Field(None, exclude=True)

    # todo: this is irrelevant in the 5-layer dispatch
    def origin_dist(self) -> int:
        """
        Compute distance from the current chained registries to :attr:`origin`.

        Returns ``-1`` for inline, ``0`` for the local registry, ``1..n`` for
        ancestors, and a large sentinel when called outside a chained context.
        """
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
        """
        Return True if this behavior participates in the given ``task``.

        Inline behaviors always match. Otherwise, compares the explicit
        behavior :attr:`task` or the origin registry’s ``task`` (if set).
        """
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
        """
        Compose selection criteria for this behavior, merged with its origin
        registry’s criteria. Includes ``is_instance`` when :attr:`caller_cls`
        is known; origin registry keys win on conflict.
        """
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
        Return the stable ordering tuple used by Behavior registries.

        Default order (most significant → least):

        1. ``priority`` (lower runs first; later handlers can clobber)
        2. ``-origin_dist()`` (closer registry shadows farther ones)
        3. ``-handler_layer()`` (INLINE > GLOBAL)
        4. ``-mro_dist(caller)`` (subclass beats superclass)
        5. selector ``specificity`` (fewer → more → most)
        6. ``handler_type`` (STATIC < CLASS < INSTANCE)
        7. ``seq`` (registration order, for tie-breaking)

        If ``by_origin`` is True, origin/layer take precedence over priority to
        preserve ancestor order when building namespaces (i.e., origin distance
        becomes the primary key).
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
        Return a callable with the correct binding for ``self.handler_type``.

        Mapping
        -------
        - :data:`STATIC` / :data:`INSTANCE_ON_CALLER` → return ``func``
          (expects ``caller`` as first positional argument).
        - :data:`CLASS_ON_CALLER` → bind to ``caller.__class__``.
        - :data:`CLASS_ON_OWNER` → bind to :attr:`owner_cls`.
        - :data:`INSTANCE_ON_OWNER` → dereference :attr:`owner` (weakref) and
          bind to that instance; raises ``RuntimeError`` if missing.

        The returned callable is always invoked as
        ``bound(caller, *args, ctx=..., **params)`` by :meth:`__call__`.
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

    def __call__(self, caller: CT, *args, ctx = None, **kwargs) -> CallReceipt:
        """
        Invoke the wrapped behavior and return a :class:`CallReceipt`.

        Parameters
        ----------
        caller:
            The runtime caller (usually a :class:`~tangl.core.Entity`).
        *args, **kwargs:
            Forwarded to the underlying function. ``ctx`` is a reserved kwarg
            propagated by the dispatch pipeline.
        """
        # bind func, call func, wrap in receipt
        logger.debug(f"type: {self.handler_type.name}, ctx: {ctx}, args: {args!r}, kwargs: {kwargs}")
        bound = self.bind_func(caller)
        result = bound(caller, *args, ctx=ctx, **kwargs)
        return CallReceipt(
            behavior_id=self.uid,
            result=result,
            # could put a lambda here if we want deferred/lazy eval or iter dispatch
            ctx=ctx,
            args=args,
            kwargs=kwargs
        )

    def unstructure(self) -> StringMap:
        """
        Behaviors intentionally do not serialize because they capture callables
        and weak references. Persist references to registries/owners instead.
        """
        raise RuntimeError(f"Do _not_ try to serialize {self!r}; contains Callable, WeakRef.")

    def get_func_sig(self):
        return self._get_func_sig(self.func)

    @staticmethod
    def _get_func_sig(func):
        """
        Return the ``inspect.Signature`` for the underlying function, unwrapping
        descriptors (e.g., bound methods) to a raw function as needed.
        """
        if func is None:
            raise ValueError("func cannot be None")
        while hasattr(func, '__func__'):
            # May be a wrapped object
            func = func.__func__
        return inspect.signature(func)

    def __hash__(self) -> int:
        # delegate hash, assuming each func can only correspond to a single handler
        return hash(self.func)
