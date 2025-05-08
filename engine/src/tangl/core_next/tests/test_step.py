import tangl.core_next
from tangl.core_next import Registry, Requirement as R, Graph, Node, Template, CursorDriver
from tangl.core_next.provision.requirement import ProvisionKey as PK

def test_auto_resolve_and_continue(tmp_path):
    g = Graph()
    root = Node(label="root",
        requires={R(PK('scene','square'))})
    g.add(root); g.cursor_id = root.uid

    # template providing scene:square + actor:shopkeeper
    def build_scene(ctx):
        scene = Node(label="square",
            provides={PK('scene','square')},
            requires={R(PK('actor','shopkeeper'))},
            content_tmpl="The {{ actor.name }} greets you.")
        return scene
    t_scene = Template(label="tpl_scene",
        provides={PK('scene','square')}, requires={R(PK('actor','shopkeeper'))},
        build=build_scene)

    # template for shopkeeper
    def build_actor(ctx):
        return Node(label="bob",
            provides={PK('actor','shopkeeper')},
            locals={"name": "Bob"})
    t_actor = Template(label="tpl_actor",
        provides={PK('actor','shopkeeper')}, build=build_actor)

    templates = Registry()
    templates.add_all(t_scene, t_actor)

    journal = list()
    driver = CursorDriver(graph=g, templates=templates, journal=journal)
    driver.step()

    assert g.find_one(label="square")
    assert journal[-1].content == "The Bob greets you."
