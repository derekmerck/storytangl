from pprint import pprint

from tangl.story import Scene
from tangl.story.scene.md2scene import md2scene, tree2scene
from tangl.utils.md2yaml import doc2tree

import pytest

# language=markdown
scene_md = """
# My Scene

#story

```yaml
if: 'abc==123'
do: 'abc=321'
```

## John Doe {.role}

```yaml
adopts: xy, _1s
```

![pic of char](char_jd_uri.jpg)

[a link](link_uri.md){#link_id}

## Start

some text for def

a second paragraph

> [!john-doe] John Doe
> blah blah blah

  - \> [do this](#override_id)
  - \> [do that](#)

An anonymous block that continues from start.

## Block 2
^override_id

You reached the end.

  - \> [done](main_menu) #done

"""

expected_tree = {'children': [{'meta': {'label': 'My Scene', 'id': 'my-scene', 'tags': ['story'], 'if': 'abc==123', 'do': 'abc=321'}, 'children': [{'meta': {'label': 'John Doe', 'id': 'john-doe', 'classes': ['role'], 'adopts': 'xy, _1s', 'images': [('char_jd_uri.jpg', 'pic of char', '')], 'refs': [('link_uri.md', 'a link', 'link_id')]}}, {'content': 'some text for def\n\na second paragraph\n\n::: {.john-doe label="John Doe"}\n> blah blah blah\n:::', 'meta': {'label': 'Start', 'id': 'start'}, 'children': [{'content': '\\>', 'meta': {'untree_as': 'list', 'refs': [('#override_id', 'do this', '')]}}, {'content': '\\>', 'meta': {'untree_as': 'list', 'refs': [('#', 'do that', '')]}}]}, {'content': 'An anonymous block that continues from start.', 'meta': {'id': 'anon'}}, {'content': 'You reached the end.', 'meta': {'label': 'Block 2', 'id': 'override_id'}, 'children': [{'content': '\\>', 'meta': {'untree_as': 'list', 'refs': [('main_menu', 'done', '')], 'tags': ['done']}}]}]}]}

@pytest.mark.xfail(reason="changed output expectation")
def test_tree2scene():
    root = doc2tree(scene_md, flat=False)
    print( root.to_dict() )
    assert root.to_dict() == expected_tree
    scene = tree2scene(root.children[0])
    pprint(scene)

    sc = Scene( **scene )
    print( sc )

@pytest.mark.xfail(reason="changed output expectation")
def test_md2scene():
    scene = md2scene(scene_md)
    sc = Scene( **scene )
    print( sc )
