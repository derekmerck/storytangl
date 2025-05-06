import tangl.core_next
from tangl.core_next import ProvisionKey as PK, Registry

def test_auto_resolve_and_continue(tmp_path):
    g = tangl.core_next.node.Graph()
    root = tangl.core_next.node.Node(label="root",
        requires={tangl.core_next.base.ProvisionKey('scene','square')})
    g.add(root); g.cursor_id = root.uid

    # template providing scene:square + actor:shopkeeper
    def build_scene(ctx):
        scene = tangl.core_next.node.Node(label="square",
            provides={PK('scene','square')},
            requires={PK('actor','shopkeeper')},
            content_tmpl="The {{ actor.name }} greets you.")
        return scene
    t_scene = tangl.core_next.template.Template(label="tpl_scene",
        provides={PK('scene','square')}, requires={PK('actor','shopkeeper')},
        build=build_scene)

    # template for shopkeeper
    def build_actor(ctx):
        return tangl.core_next.node.Node(label="bob",
            provides={PK('actor','shopkeeper')},
            locals={"name": "Bob"})
    t_actor = tangl.core_next.template.Template(label="tpl_actor",
        provides={PK('actor','shopkeeper')}, build=build_actor)

    templates = Registry()
    templates.add_all(t_scene, t_actor)

    journal = list()
    driver = tangl.core_next.cursor.CursorDriver(graph=g, templates=templates, journal=journal)
    driver.step()

    assert g.find_one(label="square")
    assert journal[-1].content == "The Bob greets you."
