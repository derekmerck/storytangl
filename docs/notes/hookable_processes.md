Dispatch Tasks
--------------

Global:  Add behaviors for basic entities to the global registry (e.g., 'init')
System:  Add behaviors to a process registry, hook globals or new tasks reflect process-level features (e.g., 'planning' or 'update' for vm)
Application: Add behaviors to a domain registry, hook globals or sys level, new tasks reflect domain-specific features (e.g., 'render' for story)
Authors: Add behaviors to the world registry that governs a given graph
Local: Add behaviors directly to an instance participant in dispatch (i.e., cursor, context, or graph)

core/global hooks:
- on_create:   cls, attrs -> new cls, attrs   # create story, node (world not loaded yet)
- on_init:     obj        -> in place          # init story, node (world not init'd yet)
- on_un/link:  Edge       -> in place          # un/link nodes
- on_index:    Reg, item

vm/system hooks:
- on_get_ns:     domain     -> map
- on_validate:   anchor     -> bool
- on_pre/postreq: anchor    -> Edge
- on_planning:   anchor     -> in place
- on_update:     anchor     -> in place
- on_render:     anchor     -> Fragments
- on_finalize:   anchor     -> in place

story/app hooks:
- on_create_world: cls, attrs -> new cls, attrs
- on_init_world: world      -> in place
- on_describe:   resource   -> Fragments

media/app hooks:
- on_index_media:  MediaRIT -> MediaRIT
- on_create_media: resource -> MediaRIT

discourse/app hooks:
- on_create_dialog: resource -> map

service/system hooks:
- on_request     request    -> request
- on_response    response   -> response
