import io

import networkx as nx
import pygraphviz as pgv
from PIL import Image

HUB_NODE_THRESHOLD = 4
NUM_CLUSTERS = 10

# SVG_DIR = MEDIA_BASE_PATH / "svg"

def ignore_node( uid, blocks ) -> bool:
    try:
        node = list(filter(lambda x: x['uid'] == uid, blocks))[0]
        return uid == "bl--1" or \
            node.get('label', '').lower().startswith("generic")
    except IndexError:
        return True


def ignore_edge( uid, t_uid, blocks ) -> bool:
    return ignore_node(t_uid, blocks) or ignore_node(uid, blocks)


def color( node ):
    match node.get('obj_cls', '').lower():
        case 'concept':
            return 'blue'
        case 'structure':
            return 'cyan'
        case 'game':
            return 'yellow'


def graph_scenes( scenes: list ):

    # Create a directed graph
    G = nx.DiGraph()

    for sc in scenes:
        add_scene( G, sc )

    plot_graph( G, cluster=True )


if __name__ == "__main__":
    graph_scenes(world.story_templates['scenes'])
