import io
import itertools
from pprint import pprint
from pathlib import Path

import attr
import networkx
import networkx as nx
import pygraphviz as gv
import yaml
from PIL import Image

from tangl.world import World
from tangl.story.scene import Scene, Block

HUB_NODE_THRESHOLD = 4
NUM_CLUSTERS = 10

@attr.define
class WorldGraph:
    """
    Input a world, generate a graph.

    Note the graph is in _reduced_ form, singly-connected linear paths of nodes have been collapsed into a single node.

    Optionally, cluster blocks into scenes and sort clustered nodes into dfs-order.  This returns the complete, _unreduced_ form.
    """

    world: World
    include_images: bool = True
    cluster_by_community: bool = False
    cluster_by_scenes: bool = True
    total_nodes: int = -1
    collapsed_nodes: int = -1
    removed_nodes: set = attr.ib(factory=set)

    G: networkx.DiGraph = attr.ib( init=False )
    @G.default
    def _mk_G(self):
        return self.build_graph()

    def collapse_linear_paths(self, G: networkx.DiGraph):
        # Remove nodes with one predecessor and one successor using DFS
        for node in list(G.nodes()):
            predecessors = list(G.predecessors(node))
            successors = list(G.successors(node))
            if 'image_file' not in G.nodes[node] and \
                    len(predecessors) == 1 and len(successors) == 1:
                # Give pred this node and all previously removed nodes
                G.nodes[predecessors[0]]['removed'].append(node)
                G.nodes[predecessors[0]]['removed'].extend(G.nodes[node]['removed'])
                G.remove_node(node)
                G.add_edge(predecessors[0], successors[0])
                self.removed_nodes.add( node )
            if not predecessors:
                G.nodes[node]['root'] = True

    def annotate_nodes(self, G: networkx.DiGraph):
        hub_nodes = [node for node in G.nodes if
                     G.in_degree(node) > HUB_NODE_THRESHOLD and
                     G.out_degree(node) > HUB_NODE_THRESHOLD]
        # print( f"Adding hub attr to {hub_nodes}" )
        for node in hub_nodes:
            G.nodes[node]['hub'] = True

        root_nodes = [node for node in G.nodes if G.in_degree(node) == 0]
        for node in root_nodes:
            G.nodes[node]['root'] = True
        print(f"Roots = {root_nodes}")

        terminal_nodes = [node for node in G.nodes if G.out_degree(node) == 0]
        for node in terminal_nodes:
            G.nodes[node]['terminal'] = True
        print(f'Termini = {terminal_nodes}')

    def ignore_node(self, uid, all_blocks) -> bool:
        try:
            node = { v['uid']: v for v in all_blocks }[uid]
            if node.get('uid') == "bl--1" or \
               node.get('label').lower().startswith("generic"):
                return True
            return False
        except KeyError:
            return True

    def ignore_edge(self, s_uid, t_uid, all_blocks) -> bool:
        return self.ignore_node(s_uid, all_blocks) or self.ignore_node(t_uid, all_blocks)

    def add_node(self, G, bl: dict, all_blocks: list):
        uid = bl.get('uid')
        if self.ignore_node(uid, all_blocks):
            return
        G.add_node(uid)
        G.nodes[uid]['removed'] = []
        sc_uid = bl.get('sc_uid')
        G.nodes[uid]['sc_uid'] = sc_uid
        actions = bl.get('actions')
        for action in actions:
            t_uid = action['target_block_id']
            if not self.ignore_edge(uid, t_uid, all_blocks):
                G.add_edge(uid, t_uid)
            # else:
            #     print(f'ignoring edge {uid}:{t_uid}')

        if not actions:
            G.nodes[uid]['improper_terminal'] = True

        # if bl.is_entry:
        #     G.nodes[uid]['entry'] = True
        if im := bl.get('media', {}).get('images', {}).get('narrative', {}).get('file'):
            G.nodes[uid]['image_file'] = self.world.get_media( fn=im )
            # print( im )
            # print( self.world.get_media( fn=im ) )

    def build_graph(self):

        # Create a directed graph
        G = nx.DiGraph()
        scenes = self.world.story_templates['scenes']
        all_blocks = [ bl | {'sc_uid': sc['uid'] } for sc in scenes.values() for bl in sc['blocks'].values() ]
        # print( all_blocks )

        for bl in all_blocks:
            self.add_node(G, bl, all_blocks)

        self.total_nodes = len( G )
        self.collapse_linear_paths(G)
        self.annotate_nodes(G)

        self.collapsed_nodes = len( G )
        print(f"Found {self.total_nodes} nodes, reduced to {self.collapsed_nodes}")

        return G

    cc: list = attr.ib( init=False )
    @cc.default
    def _mk_cc(self):
        return self.get_communities()

    def get_communities(self):
        # Identify connected components
        cc = list(nx.community.greedy_modularity_communities(self.G, best_n=NUM_CLUSTERS))
        # print(cc)
        community_nodes = sum( [ len(v) for v in cc] )
        print( f'Found {community_nodes} nodes in communities' )
        assert community_nodes == self.collapsed_nodes
        return cc

    A: gv.AGraph = attr.ib( init=False )
    @A.default
    def _mk_A(self):
        return self.to_agraph()

    def to_agraph(self):

        G = self.G
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
            if self.include_images and 'image_file' in g_node:
                node.attr['image'] = g_node['image_file']
                node.attr['imagescale'] = True
                if 'emb' in str(g_node['image_file']):
                    node.attr['width'] = '1'
                    node.attr['height'] = '1'
                else:
                    node.attr['width'] = '1.25'
                    node.attr['height'] = '2'
                node.attr['fixedsize'] = True
                node.attr['shape'] = "box"
                node.attr['labelloc'] = 't'

            # if "hub" in g_node:
            #     for edge in A.edges():
            #         if edge[0] == node:
            #             edge.attr['weight'] = 10

            # if "terminal" in g_node:
            #     for edge in A.edges():
            #         if edge[1] == node:
            #             edge.attr['weight'] = 0.5

        # Push one node below another for display
        # A.add_edge(root_node, '169', color="invis")

        if self.cluster_by_community:
            # Identify connected components
            for i, component in enumerate(self.cc):
                # Create a new subgraph
                S = A.add_subgraph(component, name=f"cluster_{i}", color='blue')
        elif self.cluster_by_scenes:
            # identify scenes from node annotations and add subgraphs
            pass

        # Use 'dot' layout for hierarchical layouts
        A.layout(prog='dot')
        return A

    @classmethod
    def _plot(cls, A: gv.AGraph, format="png"):
        # Render the graph to file (you can also use other formats like PNG, PDF, etc.)
        png_data = A.draw(format=format)
        # Convert the byte data to a PIL Image
        image_stream = io.BytesIO(png_data)
        im = Image.open(image_stream)
        im.show()

    def plot(self, format="png"):
        self._plot( self.A, format )

    @staticmethod
    def dfs_order(graph, start_node=None):
        """Return a list of nodes in DFS order."""
        return list(nx.dfs_preorder_nodes(graph, source=start_node))

    def build_scene_graph(self, roots=None):
        roots = roots or []
        H = networkx.DiGraph()

        # 'cc' gives clusters as sets of nodes, we add each cluster as a single node
        for i, cluster in enumerate(self.cc):

            cluster_root = None
            for root in roots:
                if root in cluster:
                    cluster_root = root
                    break

            H.add_node(frozenset(cluster), root=cluster_root, label=f"c{i} ({cluster_root})")
            # using frozenset as an immutable representation of a cluster

        # ccd = [ item for list in self.cc for item in list ]
        # print( ccd )
        # assert( "bl-218" in ccd )

        from pprint import pprint

        # Add edges between scenes if there's any edge between their blocks in G
        for scene1, scene2 in itertools.permutations(H.nodes(), 2):
            s1 = H.nodes()[scene1]['label']
            s2 = H.nodes()[scene2]['label']
            # print( f"----{s1}--->{s2}----")
            for block1 in scene1:
                for block2 in scene2:
                    if self.G.has_edge(block1, block2):
                        # print( f"edge: {s1}:{block1}, {s2}:{block2}" )
                        H.add_edge(scene1, scene2)
                        break
        return H

    def ordered_blocks(self, roots = None):

        roots = roots or []
        scenes_graph = self.build_scene_graph( roots=roots )
        #
        # print( f"Found { len(scenes_graph) } nodes in scene-sorted graph" )
        # print( f"Found { sum( [len(v) for v in scenes_graph ] )} total nodes in H")

        GG = nx.DiGraph( scenes_graph )
        A = nx.nx_agraph.to_agraph(GG)
        A.layout('dot')
        # self._plot(A)

        start_scene = None
        for sc_node in scenes_graph.nodes():
            if 'bl-0' in sc_node:
                start_scene = sc_node

        # Step 2: DFS on scenes graph to get ordered scenes
        ordered_scenes = self.dfs_order(scenes_graph, start_node=start_scene)
        assert len(ordered_scenes) == len(scenes_graph)

        # print( len( ordered_scenes ) )

        # Step 3 & 4: DFS on each scene's subgraph and construct the ordered data
        ordered_data = []

        for scene in ordered_scenes:
            H_node = scenes_graph.nodes()[scene]
            label = H_node['label']
            sc_root = H_node['root']
            subgraph = self.G.subgraph(scene)
            ordered_blocks = self.dfs_order(subgraph, start_node=sc_root)
            try:
                assert len(ordered_blocks) == len(subgraph)
            except AssertionError:
                # There are secondary roots, nodes that are not descendents of the local cluster's root.  Linked in from another cluster.
                diff = scene.difference( set(ordered_blocks) )
                print( f"Addending secondary root nodes: {diff}")
                ordered_blocks.extend( list(diff) )
            ordered_data.append(ordered_blocks)

        num_ordered_blocks = sum( [len(v) for v in ordered_data] )
        # print( f"Found {num_ordered_blocks} nodes in ordered data")
        assert num_ordered_blocks == self.collapsed_nodes

        return ordered_data

    def expanded_ordered_blocks(self, roots=None):
        ordered_blk_uids = self.ordered_blocks(roots=roots)

        res = []
        for i, grp_uids in enumerate( ordered_blk_uids ):
            res_ = []
            for blk_uid in grp_uids:
                uids = [ blk_uid ]
                G_node = self.G.nodes()[blk_uid]
                # print( G_node.get('removed', []) )
                uids.extend( G_node['removed'] )
                res_.extend( uids )
            res.append( res_ )

        num_expanded_ordered_blocks = sum( [len(v) for v in res] )
        print( f"Found {num_expanded_ordered_blocks} nodes in expanded ordered data")
        try:
            assert num_expanded_ordered_blocks == self.total_nodes
        except AssertionError:
            diff = self.removed_nodes.difference( set( vv for v in res for vv in v ) )
            print( f"Wrong number of expanded nodes {num_expanded_ordered_blocks} != {self.total_nodes}:  missing {diff}")

        return res

    def render_ordered_blocks(self, roots=None):
        ordered_blk_uids = self.expanded_ordered_blocks(roots)
        template_blks = {v['uid']: v for v in self.world.story_templates['scenes'][0]['blocks']}

        res = {}
        for i, grp_uids in enumerate(ordered_blk_uids):
            res_ = {}
            for blk_uid in grp_uids:
                blk_template = template_blks[blk_uid]
                res_[blk_uid] = { 'text': blk_template['text'],
                                  'choices': [{
                                      c.get('text','ok'): c['target_block_id'] } for c in blk_template['actions'] ]
                                }
            res[f'sc-{i}'] = res_
        return res


if __name__ == "__main__":
    from cwx import worlds
    cw1 = worlds[0]
    wg = WorldGraph( cw1, include_images=True, cluster_by_scenes=True )
    # set 'include_images=False' to cluster nodes slightly more efficiently
    wg.plot()
    exit()

    # roots for cw1 n=10 clusters
    roots_ = "[bl-0, bl-172, bl-5, bl-146, bl-126, bl-41, bl-176, bl-39, bl-187, bl-248]"
    roots = yaml.safe_load(roots_)

    wg.ordered_blocks( roots=roots )
    # print( wg.cc )
    eob = wg.expanded_ordered_blocks(roots)

    print( eob )

    sorted_text = wg.render_ordered_blocks(roots)
    # pprint( sorted_text, width=120, sort_dicts=False )

    # fix the yaml string repr globally
    def string_representer(dumper, data):
        if "\n" in data or len(data) > 120:
            text_list = [line.rstrip() for line in data.splitlines()]
            data = "\n".join(text_list)
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    yaml.add_representer(str, string_representer)
    sc0 = sorted_text['sc-0']
    d = yaml.dump( sorted_text['sc-0'], sort_keys=False, width=120)
    print( d )
