
from tangl.mechanics.credentials.outcomes_graph import build_graph, get_edge_colors

def test_outcomes_graph():
    G = build_graph()
    edge_colors = get_edge_colors(G)
