from tangl34.core.driver.cursor_driver import CursorDriver
from tangl34.core.structure.node import Node
from tangl34.core.structure.graph import Graph


def test_cursor_driver_advance(monkeypatch):
    # Patch service calls to record order
    call_order = []
    monkeypatch.setattr("tangl34.core.driver.cursor_driver.gather_context",
                        lambda *a, **k: call_order.append("gather_context") or {})
    monkeypatch.setattr("tangl34.core.driver.cursor_driver.resolve_requirements",
                        lambda *a, **k: call_order.append("resolve_requirements") or True)
    monkeypatch.setattr("tangl34.core.driver.cursor_driver.requires_choice",
                        lambda when, *a, **k: call_order.append(f"requires_choice_{when}") or None)
    monkeypatch.setattr("tangl34.core.driver.cursor_driver.apply_effects",
                        lambda when, *a, **k: call_order.append(f"apply_effects_{when}") or None)
    monkeypatch.setattr("tangl34.core.driver.cursor_driver.render_fragments",
                        lambda *a, **k: call_order.append("render_fragments") or [])

    r = Node(label="root")
    n = Node(label="test")
    g = Graph()
    g.add(n)
    g.add(r)
    e = g.add_edge(r, n)
    drv = CursorDriver(cursor=n, graph=g, journal=[], scopes=[])
    drv.advance_cursor(choice=e)
    assert call_order == [
        "resolve_requirements",
        "requires_choice_before",
        "requires_choice_after"
    ]