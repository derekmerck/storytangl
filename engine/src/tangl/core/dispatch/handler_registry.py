# tangl/core/dispatch/handler_registry.py
from __future__ import annotations
from typing import Iterator, Optional, Iterable

from tangl.type_hints import StringMap
from tangl.core.registry import Registry
from .handler import Handler, HandlerFunc
from .job_receipt import JobReceipt

class HandlerRegistry(Registry[Handler]):

    def add(self, func: HandlerFunc, **attrs):
        h = Handler(func=func, reg_number=len(self), **attrs)
        super().add(h)

    def register(self, **attrs):
        def decorator(func: HandlerFunc):
            self.add(func, **attrs)
            return func
        return decorator

    def find_all(self, **criteria) -> Iterator[Handler]:
        yield from sorted(super().find_all(**criteria))

    def run_one(self, ns: StringMap, **criteria) -> Optional[JobReceipt]:
        _handlers = self.find_all(**criteria)
        h = next(_handlers, None)
        return h(ns) if h else None

    def run_all(self, ns: StringMap, **criteria) -> Iterator[JobReceipt]:
        _handlers = self.find_all(**criteria)
        for h in _handlers:
            yield h(ns)

    @classmethod
    def run_handlers(cls, ns: StringMap, handlers: Iterable[Handler]) -> Iterator[JobReceipt]:
        # useful when merging handlers from multiple sources
        # deterministic ascending order: FIRST→LAST, reg_number, uid
        _handlers = sorted(handlers)
        for h in _handlers:
            yield h(ns)

DEFAULT_HANDLERS = HandlerRegistry()
