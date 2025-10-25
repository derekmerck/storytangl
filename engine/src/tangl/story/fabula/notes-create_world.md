How create world _should_ work.

```yaml
ScriptMeta:
Actors:
  - label: actor1
Scenes:
- label: scene1
  roles: actor1
  blocks:
    - label: start
```

The global Actors section are _affordances_.  We can create the affordances in create_world, then let the planner take care of creating them on the graph when they are in scope/needed.

```python
def create_world():
  graph = g
  for tmpl in script['Actors']:
      tmpl = dict(tmpl)
      tmpl.setdefault('obj_cls': Actor)
      Affordance(graph=g, template={obj_cls: Actor, **tmpl})  # open source with resolved dest
```

- On init, the cursor goes to scene1.start.
- We identify the dep on the scene as we _enter_ the scene subgraph and land on the source node, 'start'.
- The provisioner prefers to resolve the dep with an existing node, so it attaches the affordance dest, either by linking/relinking the existing affordance, or just assigning the actor node to the dep edge.

Similarly, blocks might be affordance templates at the scene level.  I'm not sure about this tho, since one cardinal rule is that only structure nodes have deps, to avoid recursion craziness, loops, etc.  So allowing a structure node to depend on a structure node would open that same door.