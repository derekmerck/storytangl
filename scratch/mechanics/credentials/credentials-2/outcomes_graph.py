"""
Graph visualization of how indications and presentations map to desired outcomes.

requires: networkx, matplotlib
"""
import networkx as nx
import matplotlib.pyplot as plt

from tangl.mechanics.credentials.enums import *

def show(G: nx.DiGraph, edge_colors = None):

    # Position nodes using a multipartite layout
    pos = nx.multipartite_layout(G, subset_key="subset")

    nx.draw(G,
            edge_color=edge_colors,
            with_labels=True,
            # labels=labels,
            pos=pos,
            node_size=90,
            font_size=9,
            font_color="black")
    plt.show()

def get_edge_colors(G: nx.DiGraph) -> list:

    def paths_for_outcome(target_ref: Outcome):

        start_nodes = [node for node in G.nodes if G.nodes[node]['subset'] == '1-indication']

        paths = []
        for start_node in start_nodes:
            paths.extend(nx.all_simple_paths(G, source=start_node, target=target_ref))
        return paths

    def paths_to_edges(paths: list):
        path_edges = set()
        for path in paths:
            for i in range(len(path) - 1):
                path_edges.add((path[i], path[i + 1]))
        return path_edges

    arrest_paths = paths_for_outcome(Outcome.ARREST)
    arrest_edges = paths_to_edges(arrest_paths)

    allow_paths = paths_for_outcome(Outcome.ALLOW)
    allow_edges = paths_to_edges(allow_paths)

    def edge_color(edge):
        if edge in arrest_edges:
            return 'red'
        elif edge in allow_edges:
            return 'green'
        return 'black'

    edge_colors = [edge_color(edge) for edge in G.edges()]

    return edge_colors


def build_graph(restrictions=common_restrictions):
    G = nx.DiGraph()

    # Adding nodes for each enum type
    for ind in Indication:
        G.add_node(ind, subset="1-indication", label=ind.name)
    for rl in RestrictionLevel:
        G.add_node(rl, subset="2-restriction", label=rl.name)
    for pres in Presentation:
        G.add_node(pres, subset="3-presentation", label=pres.name)
    for outcome in Outcome:
        G.add_node(outcome, subset="4-outcome", label=outcome.name)

    # Adding edges between indications and their restrictions
    for ind, rl in restrictions.items():
        G.add_edge(ind, rl)  # Indication to restriction level

    # Adding edges from restrictions to presentations based on requirements
    for pres in Presentation:
        reqs = pres.restriction_reqs()
        for ind, rl in reqs.get_pairs():
            G.add_edge(rl, pres)  # Restriction level to presentation based on requirements

    # Adding edges from presentations to outcomes
    for outcome in Outcome:
        pres_list = outcome.presentations()
        for pres in pres_list:
            G.add_edge(pres, outcome)  # Presentation to outcome

    return G


def main():
    G = build_graph()
    edge_colors = get_edge_colors(G)
    show(G, edge_colors)


if __name__ == "__main__":
    main()
