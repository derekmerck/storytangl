# tangl/core/dispatch/behavior_registry.py
"""
Behavior Registry – dispatch (v3.7.2)

Ordered, queryable registries of :class:`~tangl.core.dispatch.behavior.Behavior`
with deterministic selection and execution. A registry can represent a single
phase/task, a single layer (global/app/author/local), or a mix; registries can
also be *chained* to provide CSS‑like precedence across origins.

Why
----
Centralize behavior registration and deterministic dispatch so domains and
scopes can publish mechanics without manual wiring. The registry delegates
filtering to :class:`~tangl.core.entity.Selectable`, then applies stable
ordering using :meth:`~tangl.core.dispatch.behavior.Behavior.sort_key`, and
returns :class:`~tangl.core.dispatch.call_receipt.CallReceipt` objects for
auditing.

Key Features
------------
* **Registration** — :meth:`BehaviorRegistry.add_behavior` and
  :meth:`BehaviorRegistry.register` wrap callables into :class:`Behavior` with
  origin metadata.
* **Selection** — :meth:`BehaviorRegistry.dispatch` merges inline criteria with
  registry criteria and uses CSS‑style specificity (task, caller class, tags).
* **Chaining** — :meth:`BehaviorRegistry.chain_dispatch` combines multiple
  registries; origin distance and :class:`~tangl.core.dispatch.behavior.HandlerLayer`
  enforce stable layer precedence.
* **Stable ordering** — Behaviors are sorted by priority, origin distance,
  layer, MRO distance, selector specificity, handler type, and registration
  order; optional ``by_origin`` preserves ancestor order for namespace builds.
* **Audited execution** — Every invocation yields a :class:`CallReceipt`.

API
---
- :class:`BehaviorRegistry` — selection/dispatch over behaviors in one registry.
- :meth:`BehaviorRegistry.dispatch` — run all matching behaviors here.
- :meth:`BehaviorRegistry.chain_dispatch` — run across registries with layer precedence.
- :meth:`BehaviorRegistry.add_behavior` / :meth:`BehaviorRegistry.register` — add behaviors.
- :class:`~tangl.core.dispatch.behavior.Behavior` — behavior wrapper and sort key.
- :class:`~tangl.core.dispatch.call_receipt.CallReceipt` — audit record for each call.
"""
from __future__ import annotations
from typing import Type, Callable, Iterator, Iterable
import itertools
import logging

from pydantic import model_validator

from tangl.core import Entity, Registry
from tangl.core.entity import Selectable
from tangl.core.registry import _chained_registries
from .behavior import HandlerType, Behavior, HandlerLayer, HandlerPriority
from .call_receipt import CallReceipt

logger = logging.getLogger(__name__)

# ----------------------------
# Registry/Dispatch

class BehaviorRegistry(Selectable, Registry[Behavior]):
    """
    BehaviorRegistry(data: dict[~uuid.UUID, Behavior])

    Pipeline for invoking behaviors in deterministic order.

    A registry stores :class:`~tangl.core.dispatch.behavior.Behavior` objects
    and provides helpers to register callables, select matching behaviors using
    CSS‑like criteria, and execute them to yield :class:`CallReceipt` objects.

    Registries can be used standalone for a task/phase or chained to model
    origin layers (inline → local → author → application → global). Chaining
    preserves layer precedence via origin distance and
    :class:`~tangl.core.dispatch.behavior.HandlerLayer`.

    Why
    ----
    Encapsulate selection and execution so behavior providers can publish
    mechanics without tight coupling. Deterministic, testable pipelines are
    achieved by :meth:`Behavior.sort_key` and reproducible selection rules.

    Key Features
    ------------
    * **Registration** – :meth:`add_behavior` and :meth:`register` wrap callables
      into :class:`Behavior` with origin metadata for chaining.
    * **Selection** – :meth:`select_all_for` (inherited from :class:`Selectable`)
      merges registry and inline criteria (e.g., ``has_task``, ``caller_cls``).
    * **Execution** – :meth:`dispatch` runs behaviors from this registry;
      :meth:`chain_dispatch` runs across multiple registries with origin‑aware
      ordering. ``extra_handlers`` can be included as ad‑hoc inline behaviors.
    * **Stable ordering** – uses :meth:`Behavior.sort_key(caller, by_origin=...)`.
    * **Auditing** – each behavior call returns a :class:`CallReceipt`.

    API
    ---
    - :meth:`add_behavior` – register a :class:`Behavior` or callable.
    - :meth:`register` – decorator form of :meth:`add_behavior`.
    - :meth:`dispatch` – filter/sort/invoke behaviors in this registry.
    - :meth:`chain_dispatch` – same as :meth:`dispatch`, but across registries.
    - :meth:`all_tasks` – list non‑``None`` tasks present in this registry.
    """
    # defaults
    handler_layer: HandlerLayer | int = HandlerLayer.GLOBAL
    task: str = None

    def add_behavior(self, item, *,
                     priority: HandlerPriority = HandlerPriority.NORMAL,
                     # These params are optional hints for FuncInfo, don't set defaults
                     handler_type: HandlerType = None,
                     owner: Entity | None = None,
                     owner_cls: Type[Entity] | None = None,
                     caller_cls: Type[Entity] | None = None,
                     **attrs):
        """
        Register a :class:`Behavior` or a plain callable into this registry.

        Parameters
        ----------
        item:
            Either a :class:`Behavior` (inserted as‑is, ensuring ``origin=self``)
            or a callable to wrap.
        priority:
            Handler priority for ordering (lower runs earlier).
        handler_type, owner, owner_cls, caller_cls:
            Optional binding hints; if omitted, :class:`Behavior` infers them
            from the callable signature at validation.
        **attrs:
            Additional behavior attributes (e.g., ``task``, tags).

        Notes
        -----
        For callables, a new :class:`Behavior` is created with ``origin=self`` so
        layer metadata and origin distance are available during chaining.
        Raises ``ValueError`` for unsupported ``item`` types.
        """
        if isinstance(item, Behavior):
            if item.origin is None:
                item.origin = self
            self.add(item)
            return

        if isinstance(item, Callable):
            payload = dict(attrs)
            if handler_type is not None:
                payload["handler_type"] = handler_type
            if caller_cls is not None:
                payload["caller_cls"] = caller_cls
            if owner is not None:
                payload["owner"] = owner  # instance; Behavior will normalize/weakref
            if owner_cls is not None:
                payload["owner_cls"] = owner_cls

            h = Behavior(func=item,
                         priority=priority,
                         origin=self,
                         **payload)
            self.add(h)
            return

        raise ValueError(f"Unknown behavior type {type(item)}")

    def register(self, **attrs):
        """
        Decorator that wraps a function into a :class:`Behavior`, sets
        ``origin=self``, saves a breadcrumb on ``func._behavior``, and registers it.

        Returns the original function unchanged.
        """
        def deco(func):
            h = Behavior(func=func, origin=self, **attrs)
            self.add(h)
            func._behavior = h
            return func
        return deco

    @staticmethod
    def _iter_normalize_handlers(handlers: Iterable[Behavior | Callable]) -> Iterator[Behavior]:
        """
        Internal: normalize an iterable of behaviors or callables into behaviors.

        Used to include ``extra_handlers`` in :meth:`dispatch` and
        :meth:`chain_dispatch`.
        """
        for h in handlers or []:
            if isinstance(h, Behavior):
                yield h
            elif isinstance(h, Callable):
                yield Behavior(func=h, task=None)

    def dispatch(self, caller: Entity, *, task: str = None, ctx: dict = None, extra_handlers: list[Callable] = None, by_origin=False, **inline_criteria) -> Iterator[CallReceipt]:
        """
        Select, sort, and invoke matching behaviors from this registry.

        Parameters
        ----------
        caller:
            The runtime caller/entity used for selector matching and MRO distance.
        task:
            Convenience alias for ``has_task=...`` in ``inline_criteria``.
        ctx:
            Execution context dict passed through to each behavior.
        extra_handlers:
            Optional list of ad‑hoc callables/behaviors appended post‑selection.
        by_origin:
            If True, origin/layer precedence sorts before priority (useful for
            building namespaces where ancestor order must be preserved).
        **inline_criteria:
            Additional selection criteria merged with registry criteria.

        Returns
        -------
        Iterator[:class:`CallReceipt`]
            One receipt per invoked behavior, in deterministic order.
        """
        # explicit 'task' param is an alias for `inline_criteria['has_task'] = '@foo'`
        if task is not None:
            if 'has_task' in inline_criteria:
                # could check if they are the same, but very edge case, so just raise
                raise ValueError("Found 'task' and 'has_task' in inline_criteria")
            else:
                inline_criteria['has_task'] = task
        behaviors = self.select_all_for(selector=caller, **inline_criteria)

        # extra handlers have no selection criteria and are assumed to be opted in, so we just include them all
        if extra_handlers:
            behaviors = itertools.chain(behaviors, self._iter_normalize_handlers(extra_handlers))

        behaviors = sorted(behaviors, key=lambda b: b.sort_key(caller, by_origin=by_origin))
        logger.debug(f"Behaviors: {[b.sort_key() for b in behaviors]}")
        return (b(caller, ctx=ctx) for b in behaviors)

    @classmethod
    def chain_dispatch(cls, *registries: BehaviorRegistry, caller, task: str = None, ctx: dict = None, extra_handlers: list[Callable] = None, by_origin=False, **inline_criteria) -> Iterator[CallReceipt]:
        """
        Select, sort, and invoke matching behaviors across multiple registries.

        Behaves like :meth:`dispatch`, but combines registries and installs a
        chaining context so :meth:`Behavior.origin_dist` can compute distances.
        Sorting uses :meth:`Behavior.sort_key(caller, by_origin=...)`.
        """
        # explicit 'task' param is an alias for `inline_criteria['has_task'] = '@foo'`
        if task is not None:
            if 'has_task' in inline_criteria:
                # could check if they are the same, but very edge case, so just raise
                raise ValueError("Found both 'task' and 'has_task' in inline_criteria")
            else:
                inline_criteria['has_task'] = task

        behaviors = cls.chain_select_all_for(*registries, selector=caller, **inline_criteria)
        # could also treat this as an ephemeral registry and add it onto the registry
        # stack and sort while filtering, but it seems clearer to copy the
        # single-registry-dispatch code.
        if extra_handlers:
            behaviors = itertools.chain(behaviors, cls._iter_normalize_handlers(extra_handlers))
        with _chained_registries(registries):  # provide registries for origin_dist sort key
            behaviors = sorted(behaviors, key=lambda b: b.sort_key(caller, by_origin=by_origin))
        return (b(caller, ctx=ctx) for b in behaviors)

    def iter_dispatch(self, *args, **kwargs) -> Iterator[CallReceipt]:
        """
        Prototype for a lazy/partial dispatch interface.

        Not implemented. Future designs may yield thunks or partial receipts
        to enable streaming or speculative execution.
        """
        raise NotImplementedError()
        # We could return an iterator of handler calls that each produce a receipt:
        return (lambda: b(caller, ctx) for b in behaviors)
        # Or we could return an iterator of job receipts with lambda functions as result
        return (b.partial_receipt(caller, ctx) for b in behaviors)
        # Probably want a iter_chain_dispatch() as well for symmetry

    def all_tasks(self) -> list[str]:
        """
        Return the list of non‑``None`` behavior tasks present in this registry.
        """
        return [x.task for x in self.data.values() if x.task is not None]


# ----------------------------
# Registration Helper

class HasBehaviors(Entity):
    """
    Mixin for classes that define and auto‑annotate behaviors.

    During class creation, :meth:`__init_subclass__` annotates any functions that
    were decorated via :meth:`BehaviorRegistry.register` with ``owner_cls=cls``.
    Instance‑level annotation can be added in :meth:`_annotate_inst_behaviors`.
    """
    # Use mixin or call `_annotate` in `__init_subclass__` for a class
    # with registered behaviors

    @classmethod
    def _annotate_behaviors(cls):
        """
        Attach ``owner_cls=cls`` to behaviors declared on this class.
        """
        # annotate handlers defined in this cls with the owner_cls
        for item in cls.__dict__:
            h = getattr(item, "_behavior", None)
            if h is not None:
                h.owner_cls = cls
                # cls is either class_on_caller or class_on_owner

    @classmethod
    def __init_subclass__(cls, **kwargs):
        """
        Ensure behavior annotations are applied when the subclass is created.
        """
        super().__init_subclass__(**kwargs)
        cls._annotate_behaviors()

    @model_validator(mode="after")
    def _annotate_inst_behaviors(self):
        """
        (Planned) Annotate a *copy* of class behaviors for this instance, setting
        ``owner=self`` where appropriate. Left unimplemented pending a concrete
        registration strategy for instance‑bound behaviors.
        """
        # want to annotate and register a _copy_ of the instance (self, caller)
        # but _not_ class (cls, caller) behaviors with owner = self instead
        # of owner = cls
        ...
