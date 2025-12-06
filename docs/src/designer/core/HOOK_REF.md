Hookable Dispatch Tasks
=======================

**Global**:  Add behaviors for basic entities to the global registry (e.g., 'init')
**System**:  Add behaviors to a process registry, hook globals or new tasks reflect process-level features (e.g., 'planning' or 'update' for vm)
**Application**: Add behaviors to a domain registry, hook globals or sys level, new tasks reflect domain-specific features (e.g., 'render' for story)
**Author**: Add behaviors to the world registry that governs a given graph
**Local**: Add behaviors directly to an instance participant in dispatch (i.e., cursor, context, or graph)

core/global hooks
-----------------
- on_create:   cls, attrs -> new cls, attrs   # create story, node (world not loaded yet)
- on_init:     obj        -> in place         # init story, node (world not init'd yet)
- on_un/link:  Edge       -> in place         # un/link nodes
- on_index:    Reg, item  -> in place         # add item to reg

vm/system hooks
---------------
New tasks:
- on_get_ns:     anchor     -> map            # gather ns from structural domains
- on_validate:   anchor     -> bool           # check conditions
- on_pre/postreq: anchor    -> Edge           # check for redirects
- on_planning:   anchor     -> in place       # provision graph
- on_update/finalize: anchor -> in place      # execute effects
- on_journal:    anchor     -> Fragments      # generate artifacts

story/app hooks
---------------
Existing tasks with app-specific targets:
- on_create_world: cls, attrs -> new cls, attrs
- on_init_world: world      -> in place
- on_create_story: cls, attrs -> new cls, attrs
- on_init_story: story      -> in place
- on_link_role:  role dep   -> in place
- on_link_setting: setting dep -> in place

New tasks:
- on_render_content: resource -> Fragments

media/app hooks
---------------
Existing tasks with app-specific targets
- on_index_media:  MediaRIT -> MediaRIT
- on_render_media: resource -> MediaRIT

discourse/app hooks
-------------------
Existing tasks with app-specific targets
- on_render_dialog: resource -> map

service/system hooks
--------------------
New tasks:
- on_request     request    -> request
- on_response    response   -> response
