## StoryNode Lifecycle

The basic building-blocks of a story are the StoryNode and Story index classes.

### Class Management

1. StoryNode subclasses are registered with the base class as they are declared using `__init_subclass__`.

2. {class}`.World` instantiates a top level story-entity type (i.e., {class}`.Actor`, {class}`.Scene`, {class}`.Asset`) by _name_. If those classes have been superseded in the world, e.g., as by `MyActor(Actor)`, then nodes that reference that world will instantiate `MyActor` whenever `Actor` is called.

3. When an entity is `__new__`'d, it finds its desired class in `.World._class_map` or `.cls._class_map`
  This allows children to cast themselves up from {class}`.Block` to a subclass like {class}`ChallengeBlock`.
  If no override exists, the originally requested class is used as a default.

### Initialization

4. The class `__pre_init__` hook is called, which allows Actor, for example, to customize a set of templates and kwargs (name, origin) for a given role.  During the pre-init phase, the world is queried for templated keywords from the "templates" field.  The actual game files defining each world are just templates and parameters for specific nodes that make up a story.

5. Children entities are structured in the top-level class `__init__`, so they can be passed the `uid`, `parent`, and `index` parameters at instantiation rather than updated later.  That is, objects are instantiated leaf -> root rather than _vice versa_, as they would be using an `attrs` converter, for example.

6. Finally, world calls {meth}`.StoryNode.__init_node__` on each object and on any world hooks for a final pass through all the StoryNode fields once the entire context is stable.  This casts roles with actors, etc.

### Access

7. When the story is accessed by rendering it or acting on it, hooks on creating namespaces, rendering text, etc. may provide world-specific augmentations.  See the individual world docs for these.


### Serialization

8. Basic unstructuring uses `pickle.dump()`.  Links to Singletons like `Worlds <.World>` are converted to uid references and then re-established at unpickling in order to limit the pickled dependencies.

9. Advanced unstructring generates verbose or terse string dictionaries of kwargs for each node in the story-tree.  Terse representations discard any default or template data and replace all entity references with the entity.uid.  Re-structuring a terse representation requires calling the template engine and top-level classes from the source world.
