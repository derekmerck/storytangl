## Story Lifecycle

### Initialization

1. World receives req for new game context
2. World creates and registers all scene templates and children with the new context
3. World inits all scenes, which triggers secondary role creations, such as actors (hookable)
4. World re-inits all scenes to verify that all reference roles have been linked

{class}`Scenes <tangl.story.Scene>` and other story objects are pretty good at self-structuring from a base class map and content template data provided by the world.

Result is the {class}`~tangl.world.Context`, a registry of scenes and other objects with both shared and unique features.   The context also maintains a dictionary of global variables (referenced as "player.var" in the game namespace)


### Persistence

When the game world is not in use, it can be serialized and saved.  It is too complex to pickle natively bc of the dynamic class creations, so each object is "unstructured" into a flat kwargs-only representation and any default kwargs by subclass are discarded.  References within an entity to objects that exist in the registry are replaced with string pointers.  Entities not in the registry are flattened recursively inline.

Globals _must_ be simple vars without reference to game objs bc the entire dict is just pickled.

When a context is loaded, it is passed through the world's entity factory the same "stable" argument that prevents creating new secondary entities.  Instead, secondary entities are rereferenced from the context registry.

Globals are unpickled and restored.

```{admonition} Persistence
When using a threaded backend, it is important to use a context manager to lock the context during any operations that may mutate the game state.
```
