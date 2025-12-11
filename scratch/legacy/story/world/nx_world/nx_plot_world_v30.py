import io

import networkx as nx
import pygraphviz as pgv
from PIL import Image

HUB_NODE_THRESHOLD = 4
NUM_CLUSTERS = 10

def plot_graph( G, cluster=False ):

    # Convert NetworkX graph to PyGraphviz graph for better layout
    A = nx.nx_agraph.to_agraph(G)

    # Update node display attributes
    for node in A.nodes():
        g_node = G.nodes[node]

        if 'removed' in g_node and g_node['removed']:
            node.attr['label'] = f'{node} (merged: {", ".join(map(str, g_node["removed"]))})'
        if 'color' in g_node:
            node.attr['fillcolor'] = g_node["color"]
            node.attr['style'] = "filled"
        if 'root' in g_node:
            node.attr['fillcolor'] = "green"
            node.attr['style'] = "filled"
        if 'improper_root' in g_node:
            node.attr['fillcolor'] = "bluegreen"
            node.attr['style'] = "filled"
        if 'terminal' in g_node:
            node.attr['fillcolor'] = "red"
            node.attr['style'] = "filled"
        if 'improper_terminal' in g_node:
            node.attr['fillcolor'] = "pink"
            node.attr['style'] = "filled"
        if 'image' in g_node:
            node.attr['image'] = g_node['image']
            node.attr['imagescale'] = True
            node.attr['width'] = '1.5'
            node.attr['height'] = '2.5'
            node.attr['fixedsize'] = True
            node.attr['shape'] = "box"
            node.attr['labelloc'] = 't'

        if "hub" in g_node:
            for edge in A.edges():
                if edge[0] == node:
                    edge.attr['weight'] = 10

        # if "terminal" in g_node:
        #     for edge in A.edges():
        #         if edge[1] == node:
        #             edge.attr['weight'] = 0.5

    # Push one node below another for display
    # A.add_edge(root_node, '169', color="invis")

    if cluster:
        # Identify connected components
        cc = list(nx.community.greedy_modularity_communities(G, best_n=NUM_CLUSTERS))
        for i, component in enumerate(cc):
            # Create a new subgraph
            S = A.add_subgraph(component, name=f"cluster_{i}", color='blue')

        print( cc )

    # Use 'dot' layout for hierarchical layouts
    A.layout(prog='dot')

    # Render the graph to file (you can also use other formats like PNG, PDF, etc.)
    png_data = A.draw(format="png")
    # Convert the byte data to a PIL Image
    image_stream = io.BytesIO(png_data)
    im = Image.open(image_stream)

    im.show()
