Dispatch Tasks
--------------

Global:  Add behaviors with tasks to the global registry
App:     Add behaviors directly to the dedicated registry for that phase
Authors: Register behaviors with tasks in an Author-level registry that is fed to the frame

core hooks:
- on_create:   cls, attrs -> new cls, attrs   # create story, node (world not loaded yet)
- on_init:     obj        -> in place          # init story, node (world not init'd yet)
- on_un/link:  Edge       -> in place          # un/link nodes
- on index:    Reg, item

vm hooks:
- on_get_ns:     domain     -> map
- on_validate:   anchor     -> bool
- on_pre/postreq: anchor    -> Edge
- on_planning:   anchor     -> in place
- on_update:     anchor     -> in place
- on_render:     anchor     -> Fragments
- on_finalize:   anchor     -> in place

story hooks:
- on_create_world: cls, attrs -> new cls, attrs
- on_init_world: world      -> in place
- on_describe:   resource   -> Fragments

media hooks:
- on_index_media:  MediaRIT -> MediaRIT
- on_create_media: resource -> MediaRIT

discourse hooks:
- on_create_dialog: resource -> map

service hooks:
- on_request     request    -> request
- on_response    response   -> response
