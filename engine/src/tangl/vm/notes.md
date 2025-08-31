`tangl.vm`
==========

Interpreter/virtual machine for graph evolution.

`tangl.vm` is a simple application module, its members should ONLY depend on:
- core
- utils

provides:
- session (unit of work, load/save graph, create context, run a tick)
- context (process graph->domains->facts, capabilities at anchor)
- tick_runner(context, update_manager, phase)
- event log (create/apply update stack)
