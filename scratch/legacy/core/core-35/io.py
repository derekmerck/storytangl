from __future__ import annotations
import io, pathlib, zstandard, msgspec
from typing import Iterable, Tuple, Any

from pyrsistent import pmap, pvector, PMap, PVector

from .model import StoryIR, Shape, Node, Edge, Patch, Op     # adjust import path

# ---------------------------------------------------------------------------
# msgspec encoder/decoder with PMap/PVector hooks
# ---------------------------------------------------------------------------
from .scope import Layer, LayerStack

def _enc_hook(obj):
    from pyrsistent import PMap, PVector
    if isinstance(obj, PMap):
        return dict(obj)
    if isinstance(obj, PVector):
        return list(obj)
    if isinstance(obj, LayerStack):
        # Represent stack as list[dict] so msgspec can encode it
        return [_enc_hook(layer) for layer in obj._stack]
    if isinstance(obj, Layer):
        return {'locals': obj.locals, 'scope_id': obj.scope_id}

    raise TypeError

_encoder = msgspec.msgpack.Encoder(enc_hook=_enc_hook)
_decoder = msgspec.msgpack.Decoder()      # decode to raw python types

# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------

def snapshot(ir: StoryIR) -> bytes:
    return zstandard.compress(_encoder.encode(ir))

def restore(blob: bytes) -> StoryIR:
    raw = zstandard.decompress(blob)
    data = _decoder.decode(raw)
    return StoryIR.from_raw(data)         # you implemented this earlier

# ---------------------------------------------------------------------------
# Patch-log writer / reader
# ---------------------------------------------------------------------------

class PatchLogWriter:
    def __init__(self, fp):
        self._fp = fp
        self._buf: list[Patch] = []

    def append(self, patch: Patch):
        self._buf.append(patch)

    def close(self):
        packed = _encoder.encode(self._buf)          # encode LIST once
        self._fp.write(zstandard.compress(packed))
        self._fp.close()

class PatchLogReader(Iterable[Patch]):
    def __init__(self, fp):
        raw = zstandard.decompress(fp.read())
        self._patches: list[Patch] = msgspec.msgpack.decode(raw, type=list[Patch])
        # self._idx = 0

    def __iter__(self): yield from self._patches

    # def __next__(self):
    #     if self._idx >= len(self._patches):
    #         raise StopIteration
    #     p = self._patches[self._idx]
    #     self._idx += 1
    #     return p

# ---------------------------------------------------------------------------
# Patch applier (minimal ops for S-0)
# ---------------------------------------------------------------------------

def _set_in_pmap(base: PMap, path: Tuple[str, ...], value: Any) -> PMap:
    """Recursively copy-on-write down the path."""
    if not path:
        return value
    key, *rest = path
    cur = base.get(key, pmap())
    return base.set(key, _set_in_pmap(cur, tuple(rest), value))

def _del_in_pmap(base: PMap, path: Tuple[str, ...]) -> PMap:
    key, *rest = path
    if rest:
        cur = _del_in_pmap(base[key], tuple(rest))
        return base.set(key, cur)
    return base.remove(key)

def apply_patch(ir: StoryIR, p: Patch) -> StoryIR:
    # if p.op is Op.SET:
    #     if p.path and p.path[0] == "state":
    #         new_state = ir.state.set(p.path[1], p.after)
    #         return ir.evolve(state=new_state, tick=p.tick)

    if p.op is Op.SET and p.path[0] == "state":
        new_state = ir.state.set(p.path[1], p.after)
        return ir.evolve(state=new_state, tick=p.tick)  # ← return new IR

    if p.op is Op.DELETE and p.path and p.path[0] == "state":
        new_state = ir.state.remove(p.path[1])
        return ir.evolve(state=new_state, tick=p.tick)

    if p.op is Op.ADD_NODE:
        node: Node = p.after
        new_shape = ir.shape.set(
            "nodes", ir.shape.nodes.set(node.id, node)
        )
        return ir.evolve(shape=new_shape, tick=p.tick)

    if p.op is Op.ADD_EDGE:
        edge: Edge = p.after
        new_shape = ir.shape.set(
            "edges", ir.shape.edges.append(edge)
        )
        return ir.evolve(shape=new_shape, tick=p.tick)

    if p.op is Op.SET and p.path[0] == "layer":
        # find and mutate the layer’s locals
        scope_id = p.path[1]
        layer = next(l for l in ir.layer_stack._stack if l.scope_id == scope_id)
        key = p.path[2]  # "visited.scene"
        layer.locals = layer.locals.set(key, p.after)
        return ir.evolve(tick=p.tick)

    raise NotImplementedError(f"Patch op {p.op} for {p.path} not supported in S-0")

# ---------------------------------------------------------------------------

__all__ = [
    "snapshot", "restore", "PatchLogWriter",
    "PatchLogReader", "apply_patch"
]