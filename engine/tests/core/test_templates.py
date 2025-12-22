from pydantic import Field
import pytest

from tangl.core import GraphItem
from tangl.core.factory.template import Template
from tangl.core.factory.hierarchical_template import HierarchicalTemplate, ScopeSelectable
from tangl.core.factory.templ_factory import TemplateFactory

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
            "start": HierarchicalTemplate[Node]()  # No explicit label
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

    # 4. TemplateFactory flatten
    factory = TemplateFactory.from_root_templ(root)
    all_templs = list(factory.find_all())

    assert len(all_templs) == 2  # scene1 + start

    # 5. is_instance matching
    assert node_templ.matches(is_instance=Node)
    assert not node_templ.matches(is_instance=Scene)

    print("✅ All smoke tests pass!")

"""
**Test key behaviors:**
1. ✅ Stores `obj_cls` as field (unlike Entity which uses it only in structure())
2. ✅ Hydrates string obj_cls to Python type
3. ✅ Excludes record metadata (uid, seq, is_dirty) from serialization
4. ✅ Provides default obj_cls via `get_default_obj_cls()`
"""

def test_template_holds_obj_cls():
    """Template stores obj_cls as field, not just init param."""
    from tangl.core.graph import Node

    template = Template[Node](
        label="test",
        obj_cls=Node
    )

    assert template.obj_cls is Node
    assert template.obj_cls_ is Node


def test_template_hydrates_string_obj_cls():
    """String obj_cls gets resolved to Python type."""
    template = Template(
        label="test",
        obj_cls="tangl.core.graph.node.Node"
    )

    from tangl.core.graph import Node
    assert template.obj_cls is Node


def test_template_excludes_record_metadata():
    """uid, seq, is_dirty excluded from serialization."""
    template = Template(label="test")

    data = template.unstructure()

    assert "uid" not in data
    assert "seq" not in data
    assert "is_dirty_" not in data


def test_template_default_obj_cls():
    """Subclasses can provide default via get_default_obj_cls()."""
    from tangl.core.graph import Node

    class NodeTemplate(Template):
        @classmethod
        def get_default_obj_cls(cls):
            return Node

    template = NodeTemplate(label="test")
    assert template.obj_cls is Node

"""
**Key behaviors:**
1. ✅ `unstructure_as_template()` → script format (includes obj_cls)
2. ✅ `unstructure_for_materialize()` → entity payload (includes obj_cls, excludes metadata)
3. ✅ `structure_as_template()` → load from script
"""

def test_unstructure_as_template_roundtrip():
    """Serializing as template preserves all template data."""
    from tangl.core.graph import Node

    original = Template[Node](
        label="guard",
        obj_cls=Node,
        tags={"npc", "hostile"}
    )

    # Serialize as template
    data = original.unstructure_as_template()

    # Should have obj_cls
    assert data["obj_cls"] is Node  # or string, depending on serializer
    assert data["label"] == "guard"
    assert "hostile" in data["tags"]

    # Should NOT have instance metadata
    assert "uid" not in data
    assert "seq" not in data

    # Round-trip
    restored = Template.structure_as_template(data)
    assert restored.label == original.label
    assert restored.obj_cls == original.obj_cls


def test_unstructure_for_materialize():
    """Materializing payload has obj_cls, no template metadata."""
    from tangl.core.graph import Node

    template = Template[Node](
        label="guard",
        obj_cls=Node,
        tags={"npc"}
    )

    payload = template.unstructure_for_materialize()

    # Should have obj_cls for Entity.structure()
    assert payload["obj_cls"] is Node
    assert payload["label"] == "guard"

    # Should have tags (they're entity fields)
    assert "npc" in payload["tags"]

    # Should NOT have template metadata
    assert "uid" not in payload
    assert "seq" not in payload
    assert "is_dirty_" not in payload

"""
**Key behaviors:**
1. ✅ Auto-sets parent on children during validation
2. ✅ Computes `path` property from ancestor chain
3. ✅ `visit()` traverses entire tree depth-first
4. ✅ `get_scope_pattern()` returns fnmatch pattern for scoping
5. ✅ `unstructure_for_materialize()` excludes children (materializer handles them)
"""

def test_hierarchical_template_defaults_to_graph_item():

    assert HierarchicalTemplate.get_default_obj_cls() is GraphItem
    template = HierarchicalTemplate()
    assert template.obj_cls is GraphItem

    class SubClsTemplate(HierarchicalTemplate):
        ...

    assert SubClsTemplate.get_default_obj_cls() is GraphItem
    template = SubClsTemplate()
    assert template.obj_cls is GraphItem

def test_hierarchical_template_sets_parent():
    """Children get parent reference set automatically."""
    from tangl.core.graph import Node, Subgraph as Scene

    class SceneTemplate(HierarchicalTemplate[Scene]):
        blocks: dict[str, 'BlockTemplate'] = Field(
            default_factory=dict,
            json_schema_extra={'visit_field': True}
        )

    class BlockTemplate(HierarchicalTemplate[Node]):
        pass

    scene = SceneTemplate(
        label="scene1",
        blocks={
            "start": BlockTemplate(label="start"),
            "end": BlockTemplate(label="end")
        }
    )

    # Parents should be set
    assert scene.blocks["start"].parent is scene
    assert scene.blocks["end"].parent is scene


def test_hierarchical_template_path_computation():
    """Path computed from ancestor chain."""

    class Root(HierarchicalTemplate):
        children: dict = Field(default_factory=dict, json_schema_extra={'visit_field': True})

    root = Root(
        label="root",
        children={
            "a": Root(
                label="a",
                children={
                    "b": Root(label="b")
                }
            )
        }
    )

    assert root.path == "root"
    assert root.children["a"].path == "root.a"
    assert root.children["a"].children["b"].path == "root.a.b"


def test_hierarchical_template_visit():
    """visit() yields all templates in tree."""

    class Root(HierarchicalTemplate):
        children: dict = Field(default_factory=dict, json_schema_extra={'visit_field': True})

    root = Root(
        label="root",
        children={
            "a": Root(label="a"),
            "b": Root(
                label="b",
                children={
                    "c": Root(label="c")
                }
            )
        }
    )

    visited = list(root.visit())
    labels = [t.label for t in visited]

    # Should visit in depth-first order
    assert labels == ["root", "a", "b", "c"]


def test_hierarchical_template_scope_pattern():
    """Scope pattern generated from parent path."""

    class Root(HierarchicalTemplate):
        children: dict = Field(default_factory=dict, json_schema_extra={'visit_field': True})

    assert Root.get_default_obj_cls() is GraphItem

    root = Root(
        label="scene1",
        children={
            "block1": Root(label="block1")
        }
    )

    # Child's scope pattern should match parent path
    pattern = root.children["block1"].get_path_pattern()

    # Should match "scene1.*" (anything under scene1)
    assert pattern == "scene1.*"

    # Should match in selection criteria
    criteria = root.children["block1"].get_selection_criteria()
    assert criteria["has_path"] == "scene1.*"


def test_unstructure_for_materialize_excludes_children():
    """Children excluded when materializing (handled separately)."""

    class Root(HierarchicalTemplate):
        children: dict = Field(default_factory=dict, json_schema_extra={'visit_field': True})

    root = Root(
        label="scene1",
        children={
            "block1": Root(label="block1")
        }
    )

    payload = root.unstructure_for_materialize()

    # Should NOT have children
    assert "children" not in payload

    # Should have other fields
    assert payload["label"] == "scene1"

"""
**Key behaviors:**
1. ✅ Translates scope requirements to selection criteria
2. ✅ Supports tag-based scoping (has_ancestor_tags)
3. ✅ Supports pattern-based scoping (has_path with fnmatch)
"""
from tangl.core.factory import ScopeSelectable

def test_scope_selectable_tags():
    """req_scope_tags translates to has_ancestor_tags criteria."""
    template = ScopeSelectable(
        label="test",
        ancestor_tags={"combat", "dungeon"}
    )

    criteria = template.get_selection_criteria()

    assert criteria["has_ancestor_tags"] == {"combat", "dungeon"}


def test_scope_selectable_pattern():
    """req_scope_pattern translates to has_path criteria."""
    template = ScopeSelectable(
        label="test",
        path_pattern="scene1.block*"
    )

    criteria = template.get_selection_criteria()

    assert criteria["has_path"] == "scene1.block*"


def test_scope_selectable_combined():
    """Both tags and pattern work together."""
    template = ScopeSelectable(
        label="test",
        ancestor_tags={"combat"},
        path_pattern="scene1*"
    )

    criteria = template.get_selection_criteria()

    assert criteria["has_ancestor_tags"] == {"combat"}
    assert criteria["has_path"] == "scene1*"

"""
**Key behaviors:**
1. ✅ `from_root_templ()` flattens hierarchy via visit()
2. ✅ All templates registered with paths
3. ✅ `materialize_templ()` creates entities
4. ✅ Inherits all Registry search capabilities (find_one, find_all, etc.)
"""


def test_factory_from_root_templ():
    """TemplateFactory flattens hierarchy into flat registry."""
    from tangl.core.graph import Node

    class Root(HierarchicalTemplate[Node]):
        children: dict = Field(default_factory=dict, json_schema_extra={'visit_field': True})

    root = Root(
        label="root",
        obj_cls=Node,
        children={
            "a": Root(label="a", obj_cls=Node),
            "b": Root(
                label="b",
                obj_cls=Node,
                children={
                    "c": Root(label="c", obj_cls=Node)
                }
            )
        }
    )

    factory = TemplateFactory.from_root_templ(root)

    # Should have all templates
    all_templs = list(factory.find_all())
    assert len(all_templs) == 4  # root + a + b + c

    # Should be able to find by label
    a_templ = factory.find_one(label="a")
    assert a_templ is not None
    assert a_templ.path == "root.a"


def test_factory_find_by_path():
    """Can find templates by path."""

    class Root(HierarchicalTemplate):
        children: dict = Field(default_factory=dict, json_schema_extra={'visit_field': True})

    root = Root(
        label="scene1",
        children={
            "block1": Root(label="block1"),
            "block2": Root(label="block2")
        }
    )

    assert root.is_instance(GraphItem)
    factory = TemplateFactory.from_root_templ(root)

    # Find by exact path
    assert "scene1.block1" in factory.all_paths()

    block1 = factory.find_one(path="scene1.block1")
    assert block1.label == "block1"

    # todo: this is a bit confusing -- you can match by full path attrib, but you can't test has_path(pattern) or has_ancestor_tags() bc they are NOT graph items/selectors.  It seems equally confusing to let them be selectors and mirror the has_x functions manually onto them.  i.e., `factory.find_one(has_path="scene1.block1")` -> None


def test_factory_materialize_templ():
    """materialize_templ creates entity from template."""
    from tangl.core.graph import Node

    template = Template[Node](
        label="test_node",
        obj_cls=Node,
        tags={"test"}
    )

    node = TemplateFactory.materialize_templ(template)

    # Should be Node instance
    assert isinstance(node, Node)
    assert node.label == "test_node"
    assert "test" in node.tags


def test_factory_materialize_hierarchical():
    """Materializing hierarchical template creates single node (no children)."""
    from tangl.core.graph import Subgraph as Scene, Node

    class SceneTemplate(HierarchicalTemplate[Scene]):
        blocks: dict = Field(default_factory=dict, json_schema_extra={'visit_field': True})

    template = SceneTemplate(
        label="scene1",
        obj_cls=Scene,
        blocks={
            "block1": HierarchicalTemplate(label="block1", obj_cls=Node)
        }
    )

    # Materialize just the scene
    scene = TemplateFactory.materialize_templ(template)

    # Should be Scene instance
    assert isinstance(scene, Scene)
    assert scene.label == "scene1"

    # Children NOT materialized (that's materializer's job)
    # This just creates the single entity

"""
1. ✅ Fields marked with `visit_field=True` are traversed by `visit()`
2. ✅ Fields marked with `visit_field=True` are excluded from `unstructure_for_materialize()`
3. ✅ Auto-sets label from dict keys for visit fields
"""


def test_visit_field_metadata():
    """Fields marked visit_field are traversed."""

    class Root(HierarchicalTemplate):
        children: dict = Field(
            default_factory=dict,
            json_schema_extra={'visit_field': True}
        )
        data: dict = Field(default_factory=dict)  # Not marked

    root = Root(
        label="root",
        children={
            "a": Root(label="a")
        },
        data={"key": "value"}
    )

    visited = list(root.visit())

    # Should visit children
    assert len(visited) == 2  # root + a

    # data should NOT be visited
    assert all(isinstance(t, Root) for t in visited)


def test_set_label_from_key():
    """Dict keys auto-populate label for visit fields."""

    class Root(HierarchicalTemplate): ...

    # Don't provide label explicitly
    root = Root(
        label="root",
        children={
            "block1": {},  # No label field
            "block2": {}
        }
    )

    # Labels should be set from keys
    assert root.children["block1"].label == "block1"
    assert root.children["block2"].label == "block2"
