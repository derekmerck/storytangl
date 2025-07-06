from dataclasses import dataclass, replace
from typing import Any, Tuple
from pyrsistent import PMap, pmap
from .scope import LayerStack
from .io import Patch, Op

@dataclass(frozen=True, slots=True)
class Context:
    stack: LayerStack
    state: PMap                 # global
    tick:  int

    # ------------------------ LOOK-UPS ----------------------------------
    def var(self, dotted: str) -> Any:
        return self.stack.lookup_var(dotted, self.state)

    def behavior(self, key: str):
        return self.stack.lookup_behavior(key)

    # ------------------------ MUTATIONS ----------------------------------
    def set_var(self, dotted: str, value: Any) -> Tuple["Context", Patch]:
        """
        Supports 1‑ or 2‑component dotted keys (“player” or “player.hp”).
        Decides write‑target: current layer locals if the binding already
        exists there, otherwise global state.
        """
        head, *rest = dotted.split(".", 1)
        tail = rest[0] if rest else None

        top_layer = self.stack.top()

        # ---------------- local write -----------------
        if head in top_layer.locals or head not in self.state:
            # Prepare new nested PMap if tail is used
            if tail:
                submap = top_layer.locals.get(head, pmap())
                if not isinstance(submap, PMap):
                    submap = pmap()      # overwrite non-map
                submap = submap.set(tail, value)
                new_locals = top_layer.locals.set(head, submap)
            else:
                new_locals = top_layer.locals.set(head, value)

            top_layer.locals = new_locals
            patch = Patch(
                tick=self.tick,
                op=Op.SET,
                path=("layer", top_layer.scope_id, dotted),
                before=None,
                after=value,
            )
            return self, patch

        # ---------------- global write ----------------
        if tail:
            submap = self.state.get(head, pmap())
            if not isinstance(submap, PMap):
                submap = pmap()
            submap = submap.set(tail, value)
            new_state = self.state.set(head, submap)
        else:
            new_state = self.state.set(head, value)

        new_ctx = replace(self, state=new_state)
        patch = Patch(
            tick=self.tick,
            op=Op.SET,
            path=("state", dotted),
            before=None,
            after=value
        )
        return new_ctx, patch

    # Syntactic sugar
    @property
    def vars(self):
        # ctx.vars['abc']
        class LookupVar:
            def __getitem__(_, dotted: str) -> Any:
                return self.stack.lookup_var(dotted, self.state)
            # I guess this doesn't make sense as setitem can't return anything...
            # def __setitem__(_, dotted: str, value: Any) -> Tuple["Context", Patch]:
            #     return self.set_var(dotted, value)
        return LookupVar()
