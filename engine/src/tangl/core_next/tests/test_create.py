
import pytest

import yaml

from tangl.core_next import Graph, Node, ProvisionKey, CursorDriver, Registry, Template

# --- author YAML ---
data = """
- type: scene
  label: village_square
  provides: [ scene:village_square ]
  requires: [ actor:shopkeeper ]
  content_tmpl: "The {{ actor.name }} greets you."
- type: actor_template
  label: generic_shopkeeper
  provides: [ actor:shopkeeper ]
  build: |
      def _(ctx):
          from tangl.core.graph import Node
          return Node(obj_cls='Actor', label='bob', locals={'name': 'Bob'})
"""
# todo: need default builder that uses data

@pytest.mark.skip()
def test_create_from_templates():
    # --- compile to templates (pseudo) ---
    template_data = yaml.safe_load(data)
    templates = [ Template(**data) for data in template_data ]
    template_registry = Registry[Template]()
    template_registry.add_all(*templates)

    # --- build graph ---
    g = Graph()
    root = Node(label="root", requires={ProvisionKey('scene','village_square')})
    g.add(root)
    cursor = CursorDriver(graph=g, templates=template_registry)

    # --- exercise ---
    cursor.step()
    assert g.cursor == g.find_one(label="village_square")
    assert g.journal[-1][0].content == "The Bob greets you."
