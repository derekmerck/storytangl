`tangl.vm`
==========

Interpreter/virtual machine for graph evolution.

`tangl.vm` is a simple application module, its members should ONLY depend on:
- **core**
- **utils**

provides:
- **session** (unit of work, load/save graph, create context, run a tick)
- **context** (process graph->domains->facts, capabilities at anchor)
- **planning** (provisioner, provider, templates, builder, finder)
- **event** log (create/apply update stack)
