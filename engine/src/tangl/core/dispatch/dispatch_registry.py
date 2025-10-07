# tangl/dispatch/dispatch_registry.py
"""
Dispatch registry
-----------------
Ordered, queryable collection of :class:`~tangl.core.dispatch.handler.Handler`.
Provides convenience helpers to register callables and execute matching
handlers as a pipeline, yielding :class:`~tangl.core.dispatch.job_receipt.JobReceipt`.
"""
from __future__ import annotations
from typing import Iterator, Optional, Iterable

from tangl.type_hints import StringMap
from tangl.core.registry import Registry
from .handler import Handler, HandlerFunc
from .job_receipt import JobReceipt

class DispatchRegistry(Registry[Handler]):
    """
    DispatchRegistry(data: dict[~uuid.UUID, Handler])

    Pipeline for invoking handlers in deterministic order.

    Why
    ----
    Encapsulates selection and execution of handlers so domains/scopes can
    publish behavior without wiring. Deterministic ordering (priority → reg
    number → uid) makes results reproducible.

    Key Features
    ------------
    * **Registration** – :meth:`add` and :deco:`register` for concise handler setup.
    * **Selection** – :meth:`find_all(**criteria)<find_all>` filters by handler attributes.
    * **Execution** – :meth:`run_one` and :meth:`run_all` apply handlers to a namespace and
      return :class:`JobReceipt` objects.

    API
    ---
    - :meth:`add` – wrap a function in :class:`Handler` and insert into the registry.
    - :deco:`register` – decorator form of :meth:`add`.
    - :meth:`find_all(**criteria)<find_all>` – yield matching handlers in deterministic order.
    - :meth:`run_all(**criteria)<run_all>` – run all matching handlers; yield receipts.
    - :meth:`run_one(**criteria)<run_one>` – run the first matching handler; return a single receipt or `None`.
    - :meth:`run_handlers` – classmethod to run an external iterable of handlers.
    """

    def add_func(self, func: HandlerFunc, **attrs):
        """Register a function as a :class:`Handler` with optional metadata."""
        h = Handler(func=func, **attrs)
        self.add(h)

    def register(self, **attrs):
        """Decorator form of :meth:`add`; usage: `@registry.register(phase="plan")`."""
        def decorator(func: HandlerFunc):
            self.add_func(func, **attrs)
            return func
        return decorator

    # todo: is this is actually select_for plus criteria like phase=x?  Or keep a registry per phase?
    def find_all(self, **criteria) -> Iterator[Handler]:
        """Yield handlers matching `**criteria`, sorted FIRST→LAST, reg#, uid."""
        yield from sorted(super().find_all(**criteria))

    def run_one(self, ns: StringMap, **criteria) -> Optional[JobReceipt]:
        """Run the first matching handler against `ns`; return its :class:`JobReceipt` or `None`."""
        _handlers = self.find_all(**criteria)
        h = next(_handlers, None)
        return h(ns) if h else None

    def run_all(self, ns: StringMap, **criteria) -> Iterator[JobReceipt]:
        """Run all matching handlers against `ns`; yield :class:`JobReceipt` objects in order."""
        _handlers = self.find_all(**criteria)
        for h in _handlers:
            yield h(ns)

    @classmethod
    def run_handlers(cls, ns: StringMap, handlers: Iterable[Handler]) -> Iterator[JobReceipt]:
        """Run an explicit iterable of handlers deterministically; yield receipts."""
        # useful when merging handlers from multiple sources
        # deterministic ascending order: FIRST→LAST, reg_number, uid
        _handlers = sorted(handlers)
        for h in _handlers:
            yield h(ns)

# Default process-wide registry for ad-hoc handlers
DEFAULT_HANDLERS = DispatchRegistry(label='default_handlers')
