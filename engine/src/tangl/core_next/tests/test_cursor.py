from tangl.core_next.provision.requirement import ProvisionKey as PK
from tangl.core_next import Requirement as R, Node, Registry, Template, Graph, CursorDriver

k_scene = PK("scene","square")
k_actor = PK("actor","shop")
def build_scene(ctx):
    return Node(label="square", provides={k_scene}, requires={R(k_actor)},
                     content_tmpl="Hello {{ actor }}")
def build_actor(ctx): return Node(label="bob", provides={k_actor})
T = Registry(); T.add_all(
    Template(label="s", provides={k_scene}, requires={R(k_actor)}, build=build_scene),
    Template(label="a", provides={k_actor}, build=build_actor)
)
G = Graph(); root = Node(label="root", requires={R(k_scene)}); G.add(root); G.cursor_id = root.uid
drv = CursorDriver(graph=G, templates=T)
drv.step()
def test_cursor_moves_and_journal():
    assert G.cursor.label == "square"
    assert drv.journal and drv.journal[0].content_tmpl.startswith("Hello")