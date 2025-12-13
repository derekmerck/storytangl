# v3.7.2 dispatch namespace
from dataclasses import dataclass, field
from typing import Iterable
import logging
from uuid import UUID

from pydantic import Field, create_model

from tangl.type_hints import StringMap
from tangl.core import Graph, Subgraph, Node, BehaviorRegistry, LayeredDispatch
from tangl.core.behavior import ContextP, HandlerLayer as L, HandlerPriority as Prio

from tangl.vm.dispatch import vm_dispatch
from tangl.vm.dispatch import do_get_ns, on_get_ns

story_dispatch = LayeredDispatch(label="dispatch.story", handler_layer=L.APPLICATION)
world_dispatch = LayeredDispatch(label="dispatch.world", handler_layer=L.AUTHOR)

logger = logging.getLogger(__name__)

@dataclass
class FakeCtx:
    cursor: Node

    def get_active_layers(self) -> Iterable[BehaviorRegistry]:
        return vm_dispatch, story_dispatch, world_dispatch, self.local_behaviors

    _ns_cache: dict[UUID, StringMap] = field(default_factory=dict)

    def get_ns(self, node: Node = None, nocache=False) -> StringMap:
        node = node or self.cursor
        if nocache or node.uid not in self._ns_cache:
            logger.debug(f"getting ns for {node!r}")
            self._ns_cache[node.uid] = do_get_ns(node, ctx=self)
        return self._ns_cache[node.uid]

    local_behaviors: LayeredDispatch = field(default_factory=lambda: LayeredDispatch(label="dispatch_ctx"))


def test_get_ns(NodeL, SubgraphL, GraphL):

    g = GraphL(locals={'g_layer': 'present'})
    s = SubgraphL(graph=g, locals={'sg_layer': 'present'})
    n = NodeL(graph=g, locals={'n_layer': 'present'}, label="n")
    s.add_member(n)

    ctx = FakeCtx(cursor=n)
    ns = do_get_ns(n, ctx=ctx)

    import logging
    logging.basicConfig(level=logging.DEBUG)
    logger.debug(ns)

    assert ns == {'g_layer': 'present', 'sg_layer': 'present', 'n_layer': 'present'}

    g.locals['x'] = 'graph'
    s.locals['x'] = 'subgraph'
    s.locals['x'] = 'node'

    ns = do_get_ns(n, ctx=ctx)
    assert ns['x'] == 'node'

    @story_dispatch.register(task="get_ns")
    def _contribute_world_vars(caller: Graph, ctx=None):
        return {"w_layer": "present"}

    ns = do_get_ns(n, ctx=ctx)
    logger.debug(dict(ns))
    assert ns['w_layer'] == 'present'

    from tangl.vm.provision import Requirement, Dependency, Affordance
    m = NodeL(graph=g, locals={"foo": "bar"}, label="m")
    r = Requirement(graph=g, provider_id=m.uid)
    dep = Dependency(graph=g, source_id=n.uid, requirement=r, label='dependency')
    assert dep.satisfied

    # todo: should this handler registration go away when it goes out of context?

    ns = do_get_ns(n, ctx=ctx)
    logger.debug(dict(ns))
    assert ns['dependency'] == m

    # defaults to anchor
    anchor_ns = ctx.get_ns()
    assert ns == anchor_ns

    ns = do_get_ns(m, ctx=ctx)
    logger.debug(dict(ns))
    assert ns['foo'] == 'bar'
    assert ns['g_layer'] == ns['w_layer'] == 'present'
    assert 'sg_layer' not in ns

    m_ns = ctx.get_ns(m)
    assert ns == m_ns

    assert len(ctx.local_behaviors) == 0

    @ctx.local_behaviors.register(task="get_ns")
    def _contribute_context_vars(caller: Node, ctx=None) -> dict:
        return {'ctx_layer': 'present'}

    assert len(ctx.local_behaviors) == 1
    logger.debug( list(ctx.local_behaviors.find_all(selector=n, task="get_ns")) )

    ctx.get_ns(nocache=True)
    ns = ctx.get_ns()
    assert ns['ctx_layer'] == 'present'
