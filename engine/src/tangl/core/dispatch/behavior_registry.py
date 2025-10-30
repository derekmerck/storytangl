# tangl/core/dispatch/behavior_registry.py
"""
Behavior Registry – dispatch (v3.7.2)

Ordered, queryable registries of :class:`~tangl.core.dispatch.behavior.Behavior`
with deterministic selection and execution. A registry can represent a single
phase/task, a single layer (global/system/app/author/local), or a mix; registries
can also be *chained* to provide CSS‑like precedence across origins.

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
  order.
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

from tangl.type_hints import StringMap, Tag as Task
from tangl.core import Entity, Registry
from tangl.core.entity import Selectable
from .behavior import HandlerType, Behavior, HandlerLayer, HandlerPriority, HandlerFunc
from .call_receipt import CallReceipt

logger = logging.getLogger(__name__)
# logger.setLevel(logging.WARNING)

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
    * **Stable ordering** – uses :meth:`Behavior.sort_key(caller)`.
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
    task: Task = None

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

    @classmethod
    def _normalize_inline_criteria(cls, task, inline_criteria: StringMap = None):
        # explicit 'task' param is an alias for `inline_criteria['has_task'] = 'foo'`
        inline_criteria = inline_criteria or {}
        if task is not None:
            has_task = inline_criteria.get('has_task')
            if has_task is not None and task != has_task:
                raise ValueError(f"Found both 'task={task}' and 'has_task={has_task}' in inline_criteria")
            else:
                inline_criteria['has_task'] = task
        return inline_criteria

    @classmethod
    def _iter_normalize_handlers(cls, handlers: Iterable[Behavior | Callable]) -> Iterator[Behavior]:
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

    @classmethod
    def _dispatch_many(cls, *,
                       behaviors: Iterator[Behavior],
                       caller: Entity,
                       ctx: dict,
                       with_args: tuple[Entity, ...] = None,  # behavior *args
                       with_kwargs: StringMap = None,  # behavior **kwargs
                       task: Task = None,
                       inline_criteria: StringMap = None,
                       extra_handlers: Iterable[Behavior | Callable] = None,
                       dry_run: bool = False,
                       ):
        behaviors = list(behaviors)
        logger.debug(f"All possible behaviors {[f"{b.get_label()}(task={b.task})" for b in behaviors]!r}")

        inline_criteria = cls._normalize_inline_criteria(task, inline_criteria)
        logger.debug(f"Inline criteria: {inline_criteria!r}")

        iter_behaviors = Selectable.filter_for_selector(behaviors, selector=caller, **inline_criteria)

        # extra handlers have no selection criteria and are assumed to be opted in, so we just include them all
        if extra_handlers:
            iter_behaviors = itertools.chain(iter_behaviors, cls._iter_normalize_handlers(extra_handlers))

        behaviors = sorted(iter_behaviors, key=lambda b: b.sort_key(caller))
        logger.debug(f"Behaviors invoked: {[b.get_label() for b in behaviors]}")

        if dry_run:
            return

        with_args = with_args or ()
        with_kwargs = with_kwargs or {}

        return (b(caller, *with_args, ctx=ctx, **with_kwargs) for b in behaviors)

    def dispatch(self,
                 # Behavior invocation
                 caller: Entity, *,
                 ctx: dict,
                 with_args: tuple[Entity, ...] = None,  # behavior *args
                 with_kwargs: StringMap = None,         # behavior **kwargs

                 # Dispatch meta
                 task: Task = None,            # alias for has_task inline criteria
                 inline_criteria=None,        # additional selection criterial
                 extra_handlers: list[HandlerFunc|Behavior] = None,  # loose handlers
                 dry_run=False                # just print handlers
                 ) -> Iterator[CallReceipt]:
        """
        Select, sort, and execute matching behaviors.

        Parameters
        ----------
        caller : Entity
            Primary entity executing the task.
        ctx : Context, optional
            Execution context providing graph, namespace, etc.
        with_args : tuple[Entity, ...], optional
            Additional entities passed as positional args to behaviors.
            Example: for link operations: caller=source, with_args=(target,).
        with_kwargs : dict, optional
            Additional keyword arguments passed to behaviors.
            Example: {'status': 'active', 'force': True}.

        task : str, optional
            Filter behaviors by task (alias for inline_criteria['has_task']).
        inline_criteria : dict, optional
            Match criteria for filtering behaviors before checking to see
            if their selection criteria are met by the caller.

        extra_handlers : list, optional
            Ad-hoc behaviors to include (INLINE layer).
        dry_run : bool, default False
            If True, select and sort but don't execute.

        Returns
        -------
        Iterator[CallReceipt]
            One receipt per executed behavior.

        Notes
        -----
        The with_args and with_kwargs parameters are forwarded to behaviors.
        Behaviors receive:
            behavior(caller, *with_args, ctx=ctx, **with_kwargs)

        .. admonition:: Lazy!
            Remember, dispatch returns a receipt generator!  You have to iterate it
            to create results and produce by-products, e.g., `list(receipts)`.

        Examples
        --------
        # Simple single-entity dispatch
        dispatch(caller=action, task="validate", ctx=ctx)

        # Multi-entity operation
        dispatch(
            caller=source,
            with_args=(target,),
            task="link",
            ctx=ctx
        )

        # Pass extra parameters to behaviors
        dispatch(
            caller=item,
            with_kwargs={'status': 'active', 'required': True},
            task="validate",
            ctx=ctx
        )

        # Complex multi-entity with params
        dispatch(
            caller=merchant,
            with_args=(player, item),
            with_kwargs={'price': 100, 'currency': 'gold'},
            task="trade",
            ctx=ctx
        )
        """
        return self._dispatch_many(behaviors=self.values(),
                                   caller=caller,
                                   ctx=ctx,
                                   with_args=with_args,
                                   with_kwargs=with_kwargs,
                                   task=task,
                                   inline_criteria=inline_criteria,
                                   extra_handlers=extra_handlers,
                                   dry_run=dry_run)

    @classmethod
    def chain_dispatch(cls,
                       *registries: BehaviorRegistry,

                       # Behavior invocation
                       caller: Entity,
                       ctx: dict,
                       with_args: tuple[Entity, ...] = None,  # behavior *args
                       with_kwargs: StringMap = None,           # behavior **kwargs

                       # Dispatch meta
                       task: str = None,      # alias for has_task inline criteria
                       inline_criteria=None,  # additional selection criterial
                       extra_handlers: list[HandlerFunc | Behavior] = None,  # loose handlers
                       dry_run=False          # just print handlers
                       ) -> Iterator[CallReceipt]:
        """
        Select, sort, and invoke matching behaviors across multiple registries.

        .. admonition:: Lazy!
            Remember, dispatch returns a receipt generator!  You have to iterate it
            to create results and produce by-products, e.g., `list(receipts)`.
        """
        behaviors = itertools.chain.from_iterable(r.values() for r in registries)
        return cls._dispatch_many(behaviors=behaviors,
                                  caller=caller,
                                  ctx=ctx,
                                  with_args=with_args,
                                  with_kwargs=with_kwargs,
                                  task=task,
                                  inline_criteria=inline_criteria,
                                  extra_handlers=extra_handlers,
                                  dry_run=dry_run)

    def all_tasks(self) -> list[str]:
        """
        Return the list of non‑``None`` behavior tasks present in this registry.
        """
        return list({x.task for x in self.data.values() if x.task is not None})

    # Hashes like a pseudo-singleton
    # todo: cast bytes to a full range int suitable for hash?  Use `self._id_hash()`
    def __hash__(self) -> int:
        return hash((self.__class__, self.label))
