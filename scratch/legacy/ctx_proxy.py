from __future__ import annotations
from typing import Self, Any
from uuid import uuid4, UUID
from dataclasses import dataclass
from pyrsistent import PClass, field, pmap_field, pvector_field, PMap, pmap, PVector

class Entity(PClass):
    uid: UUID           = field(initial=uuid4)          # ordinary typed field

    # → declare your domain attributes here, all with real type hints
    foo: int           = field(initial=0)
    bar: str | None    = field(initial=None)

    # “dynamic” compartments still live in persistent containers
    state:  PMap[str, Any]   = pmap_field(key_type=str, value_type=object)
    shape_ids: PVector[UUID] = pvector_field(item_type=UUID)

    def shapes(self, registry: dict[UUID, Entity]) -> list[Entity]:
        return [ registry.get(sh_id) for sh_id in self.shape_ids ]

    # convenient alias that preserves types
    def with_(self, **kw) -> Self:
        return self.set(**kw)


@dataclass
class Context:
    shape_registry: PMap[UUID, Entity] = pmap_field(key_type=UUID, value_type=Entity)
    scope_ids: list[UUID] = field(initial=[])

    @property
    def scopes(self) -> list[Entity]:
        return [ self.shape_registry.get(sc_id) for sc_id in self.scope_ids ]


import wrapt                           # extremely thin, battle-tested proxy  ➋

class _Tracked(wrapt.ObjectProxy):
    def __init__(self, target, root_id, path, listener):
        super().__init__(target)
        self._self_path = path
        self._self_root = root_id
        self._self_listener = listener

    # intercept dotted access
    def __getattr__(self, name):
        attr = getattr(self.__wrapped__, name)
        return _Tracked(attr, self._self_root, (*self._self_path, name), self._self_listener)

    def __setattr__(self, name, value):
        if name.startswith("_self_"):
            return super().__setattr__(name, value)
        new = self.__wrapped__.with_(**{name: value})
        # emit patch
        self._self_listener(Patch(
            scope=self._self_root, op=Op.REPLACE,
            path=(*self._self_path, name), value=value, seq=next(_seq),
        ))
        # setattr(self.__wrapped__, name, value)               # local mutation OK, we still have the patch
        super().__setattr__("_Tracked__wrapped__", new)

from collections import ChainMap
from contextlib import contextmanager
from itertools import count
_seq = count()

@contextmanager
def ctx(*entities: Entity):
    log: list[Patch] = []

    def listener(patch): log.append(patch)

    # build a dotted namespace: attrs ▷ state ▷ shapes-by-label
    frame = ChainMap()            # stackable if you want nested ctx()
    for e in entities:
        # frame.maps.append(e.attrs)
        frame.maps.append(e.state)
        # attach labelled shapes into the mapping
        frame.maps.append({getattr(s, "label", f"_{i}"): s for i, s in enumerate(e.shapes)})

    proxy = _Tracked(frame,         # ChainMap behaves like a dict; proxy adds auditing
                     root_id=entities[0].id if entities else UUID(int=0),
                     path=tuple(),
                     listener=listener)

    yield proxy          # user code runs inside with-block

    # ---- exit: auditing results available here ----
    proxy.op_log = lambda: log       # cheap way to hand out the collected list


e = Entity(state={'my_var1': 123}, foo='abc')
print(e)
f = Entity(state={'my_var2': 456}, foo='def')
context = Context(scope_ids=[e.uid, f.uid])


with ctx(e, f) as self:
    self.foo        # 100
    self.bar        # 200  (because state-bar landed in namespace)
    cat.foo         # 300  (label "cat" promoted from shapes)
    patches = self.op_log()

from enum import Enum, auto
from dataclasses import dataclass


class Op(Enum):
    ADD = auto()
    REPLACE = auto()
    REMOVE = auto()

@dataclass(frozen=True, slots=True)
class Patch:
    scope: UUID          # entity id the op is rooted at
    op: Op
    path: tuple[str|int, ...]   # (“state”, "bar")  or (“shapes”, 1, "foo")
    value: Any | None
    seq: int             # monotonically increasing