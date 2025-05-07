from tangl.core_next import requirement, node, registry, template, resolver
from tangl.core_next import Requirement as R

def test_resolver_created():
    k_actor = requirement.ProvisionKey("actor", "npc")
    def build_npc(ctx): return node.Node(label="npc", provides={k_actor})
    tpl = template.Template(label="tpl", provides={k_actor}, build=build_npc)
    T = registry.Registry[template.Template]();
    T.add(tpl)
    G = node.Graph()
    root = node.Node(label="root", requires={R(k_actor)});
    G.add(root)
    resolver.Resolver.resolve(root, G, ctx={'templates': T})
    assert G.find_one(provides=k_actor).label == "npc"
