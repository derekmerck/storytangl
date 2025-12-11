from dataclasses import dataclass, field
from uuid import uuid4, UUID
from typing import Optional, Callable, Iterable

from tangl.core36 import Graph
from tangl.vm36.execution.patch import Effect, Patch, Op, canonicalize

@dataclass
class EffectBuffer:
    effects: list[Effect] = field(default_factory=list)
    journal: list[dict] = field(default_factory=list)
    _preview_cache: Optional[Graph] = None
    _dirty: bool = True

    # --- emission primitives -------------------------------------------------
    def emit(self, effect: Effect) -> None:
        self.effects.append(effect)
        self._dirty = True

    def say(self, frag: dict) -> None:
        self.journal.append(frag)

    # --- high-level helpers (IDs allocated by caller) ------------------------
    def create_node(self, alloc, cls_fqn: str, *, provenance=None, **data) -> UUID:
        uid = alloc()
        prov = provenance or ("effects", "create_node")
        self.emit(Effect(Op.CREATE_NODE, (uid, cls_fqn, data), prov))
        return uid

    def add_edge(self, alloc, src: UUID, dst: UUID, kind: str, *, provenance=None) -> UUID:
        eid = alloc()
        prov = provenance or ("effects", "add_edge")
        self.emit(Effect(Op.ADD_EDGE, (src, dst, kind, eid), prov))
        return eid

    def del_edge(self, eid: UUID, *, provenance=None) -> None:
        prov = provenance or ("effects", "del_edge")
        self.emit(Effect(Op.DEL_EDGE, (eid,), prov))

    def set_attr(self, uid: UUID, path: tuple[str, ...], value, *, provenance=None) -> None:
        prov = provenance or ("effects", "set_attr")
        self.emit(Effect(Op.SET_ATTR, (uid, path, value), prov))

    # --- projection -----------------------------------------------------------
    def to_patch(self, tick_id: UUID, *, rng_seed: int, io: Optional[Iterable[dict]] = None) -> Patch:
        return Patch(
            tick_id=tick_id,
            rng_seed=rng_seed,
            effects=tuple(canonicalize(self.effects)),
            journal=tuple(self.journal),
            io=tuple(io or ()),
        )

    # --- preview (read-your-writes) -----------------------------------------
    def preview(self, base: Graph, clone_fn: Optional[Callable[[Graph], Graph]] = None) -> Graph:
        if not self._dirty and self._preview_cache is not None:
            return self._preview_cache
        # If no base graph was provided, start from an empty Graph
        if base is None:
            try:
                g2 = Graph()
            except Exception as e:
                raise ValueError("preview() requires a base Graph or a constructible default Graph") from e
        else:
            # obtain a writable clone
            if clone_fn is not None:
                g2 = clone_fn(base)
            else:
                # Try common cloning strategies (DTO or pydantic model)
                try:
                    from tangl.vm36.execution.patch import resolve_fqn
                    g2 = Graph.from_dto(base.to_dto(), resolve_fqn)  # type: ignore[attr-defined]
                except Exception:
                    try:
                        g2 = Graph(**base.model_dump())  # type: ignore[attr-defined]
                    except Exception:
                        # Last resort: assume Graph has a clone()
                        g2 = base.clone()  # type: ignore[attr-defined]
        # apply current effects
        from tangl.vm36.execution.patch import apply_patch
        patch = Patch(tick_id=uuid4(), rng_seed=0, effects=tuple(canonicalize(self.effects)))
        apply_patch(g2, patch)
        self._preview_cache = g2
        self._dirty = False
        return g2
