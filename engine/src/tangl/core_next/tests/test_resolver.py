from tangl.core_next import Registry, Template, Graph, Node
from tangl.core_next import Requirement as R
from tangl.core_next.provision.requirement import ProvisionKey as PK
from tangl.core_next.handlers.resolver import Resolver

def test_resolver_created():
    k_actor = PK("actor", "npc")
    def build_npc(ctx): return Node(label="npc", provides={k_actor})
    tpl = Template(label="tpl", provides={k_actor}, build=build_npc)
    T = Registry[Template]();
    T.add(tpl)
    G = Graph()
    root = Node(label="root", requires={R(k_actor)});
    G.add(root)
    Resolver.resolve(root, G, ctx={'templates': T})
    assert G.find_one(provides=k_actor).label == "npc"
