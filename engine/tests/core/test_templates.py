from pydantic import Field
from tangl.core.factory.template import Factory, Template, HierarchicalTemplate

def test_smoke():
    """Everything basically works."""
    from tangl.core.graph import Node, Subgraph as Scene

    assert Template[Node].get_default_obj_cls() is Node
    assert HierarchicalTemplate[Node].get_default_obj_cls() is Node

    # 1. Generic propagation
    class SceneTempl(HierarchicalTemplate[Scene]):
        blocks: dict[str, Template] = Field(
            default_factory=dict,
            json_schema_extra={'visit_field': True}
        )

    # Should extract Scene from generic parameter
    assert SceneTempl.get_default_obj_cls() is Scene

    # 2. Hierarchy with label-from-key
    root = SceneTempl(
        label="scene1",
        blocks={
            "start": Template[Node]()  # No explicit label
        }
    )

    # Label should be set from key
    assert root.blocks["start"].label == "start"
    # Path should be computed
    assert root.blocks["start"].path == "scene1.start"

    # 3. Materialize
    node_templ = Template[Node](label="guard", tags={"npc"})
    node = node_templ.materialize()

    assert isinstance(node, Node)
    assert node.label == "guard"
    assert "npc" in node.tags

    # 4. Factory flatten
    factory = Factory.from_root_templ(root)
    all_templs = list(factory.find_all())

    assert len(all_templs) == 2  # scene1 + start

    # 5. is_instance matching
    assert node_templ.matches(is_instance=Node)
    assert not node_templ.matches(is_instance=Scene)

    print("✅ All smoke tests pass!")


if __name__ == "__main__":
    test_smoke()