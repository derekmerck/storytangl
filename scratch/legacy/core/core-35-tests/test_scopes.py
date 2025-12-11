# tests/test_scope.py
from __future__ import annotations

import dataclasses
import pytest

# Adjust these imports to your package
from tangl.core.domain import Scope, Domain, global_domain
from tangl.core.entity import Entity
from tangl.core.graph import Graph, Node


# --- Minimal "Handler" stand-in -----------------------------------------------------
@dataclasses.dataclass
class Handler(Entity):
    """A minimal stand-in for your real Handler class."""
    task: str | None = None
    name: str | None = None


# --- Helpers ------------------------------------------------------------------------
def mk_scope(label: str, locals_: dict | None = None) -> Scope:
    s = Domain(label=label)
    if locals_:
        s.add_vars(locals_)
    return s


# --- 1) Scope traversal: order, cycle-safety, global once ---------------------------

def test_scope_iter_scopes_bfs_order_cycle_safe_and_global_once():
    # Build a small explicit subscription graph with a cycle
    a = mk_scope("A", {"a": 1})
    b = mk_scope("B", {"b": 2})
    c = mk_scope("C", {"c": 3})
    d = mk_scope("D", {"d": 4})

    # A subscribes to B and C; B subscribes to D; C subscribes to B (cycle)
    a.scopes.extend([b, c])
    b.scopes.append(d)
    c.scopes.append(b)  # introduces a potential cycle

    got = [s.label for s in a.iter_scopes()]

    # Expect: self (A) → BFS over explicit scopes (B, C, D) → global last
    # (B seen before C’s referral to B; D discovered via B)
    assert got[0:4] == ["A", "B", "C", "D"]
    assert got[-1] == global_domain.label
    # No duplicates
    assert len(got) == len(set(got))


# --- 2) Namespace composition & precedence -----------------------------------------

def test_scope_iter_namespace_chainmap_precedence():
    a = mk_scope("A", {"x": "A", "a": 1})
    b = mk_scope("B", {"x": "B", "b": 2})
    g = mk_scope("G", {"x": "G", "g": 9})
    a.scopes.append(b)

    # monkeypatch global_domain.locals for this test (restore later automatically)
    old_globals = dict(global_domain.locals)
    global_domain.locals.update(g.locals)
    try:
        cm = a.get_namespace()  # ChainMap in the order of iter_scopes()
        # Precedence: nearest wins (A > B > global)
        assert cm["x"] == "A"
        assert cm["a"] == 1 and cm["b"] == 2 and cm["g"] == 9
    finally:
        global_domain.locals.clear()
        global_domain.locals.update(old_globals)


# --- 3) Handlers are gathered in scope order ---------------------------------------

def test_iter_handlers_respects_scope_traversal_order():
    a = mk_scope("A")
    b = mk_scope("B")
    a.scopes.append(b)

    # Install handlers by scope
    ha1 = Handler(label="ha1", task="tick", name="a-first")
    ha2 = Handler(label="ha2", task="tick", name="a-second")
    hb1 = Handler(label="hb1", task="tick", name="b-first")

    a.handlers.add(ha1)
    a.handlers.add(ha2)
    b.handlers.add(hb1)

    got = [h.name for h in a.iter_handlers(task="tick")]
    # Expect A's handlers first (in registry order), then B's, then global if any
    assert got == ["a-first", "a-second", "b-first"]


# --- 4) GraphScope: implicit scopes from subgraph membership (xfail until plumbed) --

@pytest.mark.xfail(reason="Pending GraphScope.find_implicit_scopes() subgraph discovery plumbing")
def test_graphscope_implicit_subgraph_scopes_are_included_once():
    g = Graph(label="G")
    # Two scopes advertised by a subgraph
    rules = mk_scope("GameRules", {"max_rounds": 5})
    ui = mk_scope("GameUI", {"theme": "crt"})
    # We’ll represent a subgraph-level scope container as a Scope for now
    container_scope = mk_scope("GameScopeContainer")
    container_scope.scopes.extend([rules, ui])

    # Create nodes + subgraph and (by convention) attach the container_scope to the subgraph
    n = g.add_node(label="N")              # GraphScope subclass
    sg = g.add_subgraph(label="GameSG", members=[n])

    # Implementation-dependent: however you anchor scopes on subgraph, one simple pattern is:
    # stash it on sg.locals or an attribute that GraphScope.find_implicit_scopes() will read.
    sg.locals["implicit_scopes"] = [container_scope]

    # Now implicit discovery should include rules and ui after explicit scopes
    names = [s.label for s in n.iter_scopes()]
    assert "GameRules" in names and "GameUI" in names
    # Still only one global
    assert names[-1] == global_domain.label


# --- 5) GraphScope: implicit scopes via class/MRO (xfail until plumbed) -------------

@pytest.mark.xfail(reason="Pending MRO-based implicit scope plumbing")
def test_graphscope_implicit_mro_scopes_from_classes():
    # Define a scope-bearing base class and a derived node type.
    base_scope = mk_scope("BaseGameScope", {"game_state": "default"})

    class GameNode(Node, Domain):
        pass

    class SinglePlayerGame(GameNode):
        pass

    # Convention: classes can carry a __scopes__ list (or similar) picked up by MRO discovery
    GameNode.__scopes__ = [base_scope]

    g = Graph(label="G")
    n = g.add_node(label="N")  # assume Graph.add_node builds a GraphScope/Node

    # If the graph creates plain Node instances, we emulate the intended target here:
    # n = SinglePlayerGame(label="N"); g.add(n)

    names = [s.label for s in n.iter_scopes()]
    assert "BaseGameScope" in names
    # Nearest-first should still hold (self, explicit, implicit[MRO], global)
    assert names[-1] == global_domain.label