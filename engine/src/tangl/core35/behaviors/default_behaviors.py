from pyrsistent import pvector

from tangl.core35.phase import Phase
from tangl.core35.dsl import compile_pred
from .behavior_registry import BehaviorRegistry

noop_behaviors = BehaviorRegistry()
stub_behaviors = BehaviorRegistry()

for ph in Phase:
    @noop_behaviors.register(ph, priority=0)
    def noop(ir, _ph=ph):      # closure keeps phase for debugging
        return ir, []

# @behaviors.register(Phase.EFFECTS)
# def mark_visited(ctx):
#     scope = ctx.stack.top().scope_id
#     return ctx.set_var(f"visited.{scope}", True)

@stub_behaviors.register(Phase.EFFECTS, priority=10)
def mark_scope_visited(ctx):
    scope = ctx.stack.top().scope_id
    return ctx.set_var(f"visited.{scope}", True)

# @behaviors.register(Phase.PREDICATE, priority=0)
# def eval_pred(ctx):
#     # simply attach compiled callable on the edge object for reuse
#     for edge in ctx.stack.top().edges:     # edges reachable from current node
#         if not hasattr(edge, "_compiled"):
#             edge._compiled = compile_pred(edge.predicate)
#     return ctx, []

@stub_behaviors.register(Phase.PREDICATE, priority=10)
def eval_pred(ctx):
    node_id = ctx.var("cursor")
    node    = ctx.var(f"{node_id}.node")

    # build list of edges whose predicate is True right *now*
    passing = []
    for e in node.outgoing:
        if compile_pred(e.predicate)(ctx):
            passing.append(e.id)          # store ids, not objects

    # put into layer locals for this tick
    top = ctx.stack.top()
    top.locals = top.locals.set(("passing_edges", node_id), pvector(passing))
    return ctx, []                   # no patches, pure read

# @behaviors.register(Phase.PROVISION)
# def spawn_child(ctx):
#     curr = ctx.stack.top().locals["cursor"]   # assume current node id stored
#     node = ctx.stack.lookup_var(f"{curr}.node")   # retrieve Node object
#     # pick first outgoing edge whose predicate is True
#     chosen = next(e for e in node.edges if e._compiled(ctx))
#
#     # scope switch
#     next_node = ctx.stack.lookup_var(f"{chosen.dst}.node")
#     ctx.stack.scope_manager.switch(node.scope_id, next_node.scope_id)
#
#     # Patch: update cursor
#     ctx, p = ctx.set_var("cursor", chosen.dst)
#     return ctx, [p]

@stub_behaviors.register(Phase.PROVISION, priority=10)
def spawn_child(ctx):
    node_id   = ctx.var("cursor")
    passing   = ctx.stack.top().locals.get(("passing_edges", node_id), pvector())
    if not passing:
        return ctx, []   # no legal edge; soft-lock logic later

    chosen_id = passing[0]                       # take first
    edge      = ctx.var(f"{chosen_id}.edge")     # you stored edges similarly

    next_node = ctx.var(f"{edge.dst}.node")
    curr_node = ctx.var(f"{node_id}.node")
    ctx.stack.scope_manager.switch(curr_node.scope_id, next_node.scope_id)

    ctx, p = ctx.set_var("cursor", edge.dst)
    return ctx, [p]