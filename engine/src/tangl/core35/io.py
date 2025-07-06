from __future__ import annotations
import io, pathlib, zstandard, msgspec
from typing import Iterable, Tuple, Any

from pyrsistent import pmap, pvector, PMap, PVector

from .model import StoryIR, Shape, Node, Edge, Patch, Op     # adjust import path

# ---------------------------------------------------------------------------
# msgspec encoder/decoder with PMap/PVector hooks
# ---------------------------------------------------------------------------

def _enc_hook(obj):
    from pyrsistent import PMap, PVector
    if isinstance(obj, PMap):
        return dict(obj)
    if isinstance(obj, PVector):
        return list(obj)
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
    def __init__(self, file: io.BufferedWriter):
        self._zw = zstandard.ZstdCompressor().stream_writer(file)

    def append(self, patch: Patch):
        self._zw.write(_encoder.encode(patch))

    def close(self):
        self._zw.flush(zstandard.FLUSH_FRAME)
        self._zw.close()

class PatchLogReader(Iterable[Patch]):
    def __init__(self, file: io.BufferedReader):
        print( "trying to create reader" )
        self._zr = zstandard.ZstdDecompressor().stream_reader(file)
        self._reader = msgspec.msgpack.Decoder(type=Patch)
        print( "created reader" )

    def __iter__(self):
        return self

    def __next__(self):
        print('called next on reader')
        try:
            result = self._reader.decode(self._zr.read())
            print( result )
            return result
        except msgspec.DecodeError:
            raise StopIteration

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
    if p.op is Op.SET:
        if p.path and p.path[0] == "state":
            new_state = ir.state.set(p.path[1], p.after)
            return ir.evolve(state=new_state, tick=p.tick)
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

    raise NotImplementedError(f"Patch op {p.op} not supported in S-0")

# ---------------------------------------------------------------------------

__all__ = [
    "snapshot", "restore", "PatchLogWriter",
    "PatchLogReader", "apply_patch"
]