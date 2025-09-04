# tangl/vm/patch.py
from __future__ import annotations
from typing import Iterable, Any
from uuid import UUID
from importlib import import_module
from dataclasses import dataclass, field
from enum import StrEnum

# from tangl.core36.types import Effect
from tangl.core36 import Graph, Node, Edge


class Op(StrEnum):
    """
    Primitive mutation kind.

    The engine canonicalizes the emitted Effects so that, for example, `DEL_EDGE` happens
    before `CREATE_NODE` when both target the same IDs. See `vm.patch.canonicalize`.
    """
    CREATE_NODE = "create_node"
    DELETE_NODE = "delete_node"
    ADD_EDGE    = "add_edge"
    DEL_EDGE    = "del_edge"
    SET_ATTR    = "set_attr"
    SET_MAPKEY  = "set_mapkey"

@dataclass(frozen=True)
class Effect:
    """
    A single mutation.

    - `op`: primitive operation (see `Op`).
    - `args`: op-specific arguments (see `vm.patch.apply_patch` for decoding).
    - `provenance`: `(phase, handler_id)` identifying who emitted the Effect
      (set by `PhaseBus.run`, visible in audit and test fixtures).
    """
    op: Op
    args: tuple[Any, ...]
    provenance: tuple[str, str] = ("?", "?")   # (phase, handler_id)

_ORDER = {Op.DELETE_NODE: 0, Op.DEL_EDGE: 1, Op.CREATE_NODE: 2, Op.ADD_EDGE: 3, Op.SET_ATTR: 4, Op.SET_MAPKEY: 5}


@dataclass(frozen=True)
class Patch:
    """
    An atomic **tick commit**.

    - `effects`: ordered sequence of `Effect`s (post-canonicalization on apply).
    - `journal`: structured, human-readable fragments for renderers.
    - `io`: deterministic IO transcripts (LLM/media calls, etc.) captured by the VM.

    **Replay model**:
    Snapshots store the graph DTO; the event log stores Patches. Replaying snapshots + patches
    reconstructs the exact surface the authors saw, including journal and IO.
    """
    tick_id: UUID
    rng_seed: int
    effects: tuple[Effect, ...]
    journal: tuple[dict, ...] = ()
    io: tuple[dict, ...] = ()

def canonicalize(effects: Iterable[Effect]) -> list[Effect]:
    # delete-before-create avoids edge/node tombstone conflicts; order stabilizes effect application.
    return sorted(effects, key=lambda e: (_ORDER[e.op], str(e.args[:2])))

def resolve_fqn(fqn: str) -> type:
    mod, qual = fqn.split(":")
    return getattr(import_module(mod), qual)

def _set_attr(obj, path: tuple[str, ...], value):
    host = obj
    *parents, leaf = path
    for seg in parents:
        host = getattr(host, seg) if hasattr(host, seg) else host[seg]
    if hasattr(host, leaf):
        setattr(host, leaf, value)
    else:
        host[leaf] = value

def apply_patch(graph: Graph, patch: Patch) -> Graph:
    for e in canonicalize(patch.effects):
        match e.op:
            case Op.CREATE_NODE:
                uid, cls_fqn, data = e.args
                typ = resolve_fqn(cls_fqn)
                node = typ(uid=uid, **data)  # Pydantic constructs surface Node/Edge/etc
                if issubclass(typ, Edge):
                    graph._add_edge_silent(node)  # edge is also GraphItem
                else:
                    graph._add_node_silent(node)
            case Op.DELETE_NODE:
                uid, = e.args
                graph._del_node_silent(uid)
            case Op.ADD_EDGE:
                src, dst, kind, eid = e.args  # include eid to avoid searching
                edge = Edge(uid=eid, src_id=src, dst_id=dst, kind=kind)
                graph._add_edge_silent(edge)
            case Op.DEL_EDGE:
                eid, = e.args
                graph._del_edge_id_silent(eid)
            case Op.SET_ATTR | Op.SET_MAPKEY:
                uid, path, value = e.args
                obj = graph.get(uid)
                if obj is None:
                    raise KeyError(f"SET_ATTR refers to missing {uid}")
                _set_attr(obj, path, value)
    return graph


@dataclass
class PatchBuffer:
    patches: list[Patch] = field(default_factory=list)

    def add(self, p: Patch) -> None:
        self.patches.append(p)

    def __len__(self): return len(self.patches)

    def flatten_effects(self) -> tuple[Effect, ...]:
        return tuple(e for p in self.patches for e in p.effects)

    def flatten_journal(self) -> tuple[dict, ...]:
        return tuple(j for p in self.patches for j in p.journal)

    def to_super_patch(self) -> Patch:
        # Optional: keep original per-effect provenance; pick a synthetic tick id
        from uuid import uuid4
        return Patch(
            tick_id=uuid4(),
            rng_seed=0,                            # purely a container
            effects=self.flatten_effects(),
            journal=self.flatten_journal(),
            io=tuple(io for p in self.patches for io in p.io),
        )
