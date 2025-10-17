The v34 handler has signature introspection and allows registration to instance domains, global domains, and class/type domains.

After considering how to create a gather namespace handler using the current framework, I think that we need to re-implement this so Nodes don't have to carry their own handlers (which gets in the way of serialization if nothing else) but can refer to class methods _as_ handlers.

see 
- `scratch/legacy/core/core-34/dispatch/handler.py`
- `scratch/legacy/core/core-34/dispatch/notes.md`