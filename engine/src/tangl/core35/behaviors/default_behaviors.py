from tangl.core35.phase import Phase
from tangl.core35.dsl import compile_pred
from .behavior_registry import BehaviorRegistry

behaviors = BehaviorRegistry()

for ph in Phase:
    @behaviors.register(ph, priority=0)
    def noop(ir, _ph=ph):      # closure keeps phase for debugging
        return ir, []

@behaviors.register(Phase.EFFECTS)
def mark_visited(ctx):
    scope = ctx.stack.top().scope_id
    return ctx.set_var(f"visited.{scope}", True)

@behaviors.register(Phase.PREDICATE, priority=0)
def eval_pred(ctx):
    # simply attach compiled callable on the edge object for reuse
    for edge in ctx.stack.top().edges:     # edges reachable from current node
        if not hasattr(edge, "_compiled"):
            edge._compiled = compile_pred(edge.predicate)
    return ctx, []

@behaviors.register(Phase.PROVISION)
def spawn_child(ctx):
    curr = ctx.stack.top().locals["cursor"]   # assume current node id stored
    node = ctx.stack.lookup_var(f"{curr}.node")   # retrieve Node object
    # pick first outgoing edge whose predicate is True
    chosen = next(e for e in node.edges if e._compiled(ctx))

    # scope switch
    next_node = ctx.stack.lookup_var(f"{chosen.dst}.node")
    ctx.stack.scope_manager.switch(node.scope_id, next_node.scope_id)

    # Patch: update cursor
    ctx, p = ctx.set_var("cursor", chosen.dst)
    return ctx, [p]