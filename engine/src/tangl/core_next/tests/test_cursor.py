from tangl.core_next import requirement, node, registry, template, cursor
from tangl.core_next import Requirement as R

k_scene = requirement.ProvisionKey("scene","square")
k_actor = requirement.ProvisionKey("actor","shop")
def build_scene(ctx):
    return node.Node(label="square", provides={k_scene}, requires={R(k_actor)},
                     content_tmpl="Hello {{ actor }}")
def build_actor(ctx): return node.Node(label="bob", provides={k_actor})
T = registry.Registry(); T.add_all(
    template.Template(label="s", provides={k_scene}, requires={R(k_actor)}, build=build_scene),
    template.Template(label="a", provides={k_actor}, build=build_actor)
)
G = node.Graph(); root = node.Node(label="root", requires={R(k_scene)}); G.add(root); G.cursor_id = root.uid
drv = cursor.CursorDriver(graph=G, templates=T)
drv.step()
def test_cursor_moves_and_journal():
    assert G.cursor.label == "square"
    assert drv.journal and drv.journal[0].content_tmpl.startswith("Hello")