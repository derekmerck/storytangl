Layers
------

1. global
- core
- audit

2. system
- vm (frame, context/ns, planning, journal)
- service (response)
- media (special planning)

3. application
- story (concept, episode, fabula)

4. author
- world (_this_ fabula, templates, assets, rules, facts)

5. user
- ancestors (_this_ graph)
- structure (_this path_)

6. inline

-----

Lower levels can plug into tasks defined at higher levels or define new tasks.
Higher levels should not make any assumptions about lower level task definitions.

Higher level invocations should admit lower level layers

```python
# vm.planning
from core import core_dispatch  
# globals, doesn't have 'on_planning' tasks, but may have helpers, auditors, or
# other features that the application layer assumes will exist
vm_dispatch = BehaviorRegistry(layer=Application)

on_do_planning = partial(vm_dispatch.register, task="do_planning")
# any lower layer that wants to participate in this task can import it from here

@on_do_planning()
def planning_task(c, *, ctx):
    ...

def do_planning(cursor: Node,
                application_dispatch=None, # static ledger type (story pkg)
                author_dispatch=None,      # static ledger initialized by factory (world)
                user_dispatch=None,        # ledger current state (this graph)
                inline=None) -> Receipts:
    return chain_dispatch(cursor,
                          core_dispatch,        # no planning, but may audit
                          vm_dispatch,          # _this_ system
                          application_dispatch, # story plugins
                          author_dispatch,      # world plugins
                          user_dispatch,        # override on this graph
                          task="do_planning",
                          inline=inline)
```


