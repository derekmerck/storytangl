Business Layer
--------------

In this case, we are abstracting away the presentation layer to support various front-end clients with different media and rendering capabilities, to be negotaited with the service layer.

Within the business layer, we have 3 cores:
- source content and scripting
- state representation and management
- narrative and media output

The central focus is state representation and management -- the abstract narrative graph and management handlers/plugins.  The ANG instance models all possible paths and concepts latent in a story.  As the story progresses nd nodes are added, relinked, and traversed, the ANG simultaneously collapses into a concrete linear 'journal' of content.  

The source layer takes definitions in human-readable format and converts them into into templates, recipes, and rules for creating and managing/hooking an ASG instance for that 'world'.  Script format is flexible, from yaml corresponding to a serialized ASG model and python handler modules, to a DSL that validates and builds its own ASG template from discovered relationships.

The output or journal layer generates, assembles, and tracks media and narrative output fragments as the ASG is traversed/collapsed.  At each narrative event, a new entry is composed for the current state and cursor on the ASG.  That entry is stored by the data layer in parallel with the ASG and its history.  Narrative and media content services may run on stand-alone nodes and be advertised for federation within a story service.


Hooks
-----

Hooks can be registered on any action mentioned, like world creation, graph creation, node entry, gather node context, sve graph, etc.  Each action is treated like a prioritized pipeline with specific expectations for arguments and expected output.  Authors may hook actions _in their world only_ and tamper with the input/output at specific points in the pipeline (updating the context last, for example, so their changes override local vars, or first, so their changes are always overwritten if a local var exists).

Hookable functions and strategy hooks are registered implicitly with decorators in the python reference library implementation.

============

so here is where we get into object-oriented philosophy.  I use a generic node for any concept, including a traversable node.  Traversable nodes are just a subclass of node.  We can add them willy-nilly and distinguish them as necessary by type.  So a graph is just a bunch of nodes of various types.  I have 4 major 'classes' of concept behaviors -- traversables/scenes/blocks, - actors and roles (an assignment edge between a traversable and an actor, different actors can be assigned to a given scene's role depending on the current state), - places and locations (indirect edge to a place, like a role), - assets, which are fungible or non-fungible and are based on a singleton instance, i.e., a discrete singleton 'sword' or a countable singleton asset 'gold'.  Discrete assets wrap their immutable singleton in a mutable node, countable assets are kept in a counter indexed by singleton type.  So we just have 'graph.add_node()' and somewhere else the story manager has to decide what kinds of nodes to add.

I subclass Node into various concepts TraversableNode, ActorNode, etc. and use typed Edges like class Role(Edge[ActorNode]) That allows me to attach behaviors directly to the different node-types and allows users to overload classes by inheriting.  Within that basic framework, I try to use composition of nodes as much as possible, so an actor might have a "look" property that returns the first child concept node of type "Look" that it can find.  Tasks are implemented as pipelines that take a generic 'Node' and each handler in the pipeline decides if it's applicable by looking at type, tags, context.  Using isa Inheritance for filtering handlers at a high level is much more powerful than just trying to keep an exhaustive list of 'type' fields that a handler applies to.

Typed Edges: Having class Role(Edge[ActorNode]) gives you static type checking and makes the code more self-documenting. Anyone reading the code instantly understands the relationship.
Behavior Inheritance: Subclassing allows you to define behaviors once for each node type and have them consistently available.
Handler Filtering: Using isinstance() checks is indeed much more efficient than string comparisons or maintaining tag lists for determining handler applicability.
Composition for Features: Using child nodes to represent features (like an actor's "look") keeps entities modular while maintaining the structural relationships.
Pipeline Pattern: The task pipeline approach that takes generic nodes and has handlers self-select based on node type creates a clean separation of concerns.

=====

- The main class for all managed object is the _Entity_, which is a pydantic model that can serialize itself and knows how to be filtered or found by various criteria including ids/hashes/names/aliases, attribute values, and truthy instance methods.  
- A _Registry_ is an Entity dictionary of entities that can be indexed/searched in various ways and serializes entire collections of entities into a single object. 
- _Singletons_ are immutable Entities that, obviously, are fixed, usually they represent system-wide globally available creator services or world-specific but immutable objects.  A singleton class has an internal registry of instances and newing a singleton twice returns an existing instance if it already exists.  

- _Nodes_ are entities with parents and children.
- _Graphs_ are registries of nodes.  Nodes always keep a reference to their graph and only refer to other nodes as id's, dereferencing them as needed.  This allows Graphs to serialize trivially without recursions.  
- _Edges_ are just nodes with a single child, which can be referenced by the successor attribute. 

- _Handlers_ are a combination of an Entity class mixin like "CanHandleTaskX" and a task pipeline "OnHandleTaskX" that work together.  Handlers can be defined anywhere and registered via a decorator, but generally live on the related mixin class or a subclass using that mixin.  When the pipeline is invoked on an entity, the pipeline filters its registered handlers by entity criteria and sorts them by priority and mro, then executes them and returns an output type defined on the pipeline, like "all true", "gather results", "pipeline results", etc.  

- A _Story World_ is a Singleton that can generate new stories based on templates and manages the set of rules/handlers for world-specific behaviors and concepts
- _Stories_ (the ASG) are graphs of story concept nodes.  
- _Story Nodes_ are just regular nodes with a few common handlers, like the ability to gather a scoped context or evaluate its own conditional availability based on the context.  

Story concept nodes are further subdivided into the 4 main functional branches:

- Traversable _Scenes_, _Blocks_ and _Actions_ (Edges connecting traversables)
- Setting _Places_ and _Locations_ (Edges connecting a traversable to a place)
- _Actors_ and _Roles_ (Edges connecting a traversable to an actor)
- _Assets_, which are either countable or discrete.  

A Story also contains some bookkeeping classes:

- The _Narrative Journal_ so far, a linear sequence of all the _Journal Fragments_ generated during traversal
- The _Traversal History_, which can, in theory be used to rewind and pop traversal steps off the current state
- A link to the source _Story World_ singleton that generated it
- And, optionally, a link to a _User Account_ that is responsible for the story, for service-level authentication and story-level tracking achievements across worlds.

The main _tasks_ of the system are:
1. Compile a world from source
2. Generate a story instance from a world's templates
3. Traverse the story node-by-node to compute a narrative thread
4. Incrementally reveal the narrative thread to a user and accept inputs
5. Optionally, track a user across worlds and stories

Traversal instructions can come from a user (make a choice), from inline logic (proceed to this node next), or from an automatic framework that might simulate a user for testing or be used to pre-render a certain thread of the story into a concrete form for an ebook, for example.

Traversal steps trigger a pipeline with several stages:
1. Check for redirections on the target (e.g., jump to a dream before waking up)
2. Check the target node is valid/available
3. Invoke any effects on the target node (update state)
4. Generate content for the node (triggers its own pipeline that may invoke related concept nodes, linked actors, and various content creators like ai gen, etc.)
5. Check for continuations on the target (e.g., after going to sleep, jump to a dream)

If no next node is returned from the traversal, the logic blocks and waits for user input.

There are a couple more broad areas of business logic:

1. Content generators or _Content Forges_, produce Text or Media Journal Fragments, a content forge uses an adapter to take data from a caller node and create a suitable recipe for itself, for example, an Actor node might be able to request an avatar from an SvgPaperDoll factory using an adapter class that knows how to map between Actor attributes and the content factories available shapes and textures.

2. Mechanics, which covers components that can be added onto story concept nodes, like Scenes/Blocks with interactive _Games_, Actors with character _Stats_ and Blocks with _Stat Challenges_, or character _Looks_ like _Outfits_ and _Ornaments_.

Business Logic Layer API
------------------------

The world and story objects present minimal public apis for their main tasks:

world:
- load a world singleton from source (rw)
- unload a world (rw)
- list all world instances (ro)
- get info about a world (ro)
- create a new story from a world (rw)

story:
- read entries from a story journal (ro)
- get info about a story (player status, maps, etc.) (ro)
- resolve a traversal step in a story (rw)
- undo a step in a story (rw) (*optional*)

story dev: (*these flag the story as 'dirty'*)
- jump to a traversable node in a story
- get info about a node in a story
- evaluate an expression in a story
- apply an effect in a story


Core
----
Basic data structures and functions for all managed entities

**Managed Entities**
- Have a unique id
- Have string "tags"
- Serializable as kv (using _pydantic_)

**Handlers**
- Class functions implementing entity behaviors
- Implements a flexible, hookable method resolution strategy that considers class-subtypes, explicit ordering, and output format

**Entity Handlers**
- Create new entity (change class, kwargs)
- Represent entity state as context (namespace)
- Runtime eval/check conditions and apply/exec effects given context
- Enable/disable entity based on conditions (available)
- Realize content given context (render)

**Singleton Entities**
- Immutable
- Serializable by name

**Graph Entities**
- Mutable, has state
- Collection of node entities
- Serializable as collection of nodes

**Node Entities**
- Mutable, has state
- Has children/parent references
- Always part of a graph

**Wrapped-Singleton Nodes**
- Wraps a singleton with instance-specific mutable state

**Indirect Connecting Nodes (Edges)**
- Generic in successor class
- Parent is predecessor
- References a successor
- Successor may be referenced, filtered, or created

**Traversable Graphs and Nodes**
- Traversable graph has a cursor reference to the 'current' node
- Cursor can be directed to follow traversable connecting nodes to a different node
- Cursor directives may be user selected or automatically triggered

**Graph and Node Handlers**
- Validate conditions and associate parent/child nodes (node-handler)
- Validate conditions and traverse edges, triggering effects, content realization, and additional cursor directives, can determine initial cursor position (graph-handler)

Story
-----
Related to organizing narrative concepts into managed entities.

**Story (Traversable Graph) and Story Nodes**
- Story holds an ordered journal of content realized during traversal
- Story nodes types are divided into 4 categories: scenes, actors, places, and assets
- Story api: `get journal entry`, `get story info`, `do story action`, `get story media`
- Story dev api: `goto node`, `inspect node`, `check expr`, `apply expr`

**Scene**
- A scene node is the root of a tree of connected block nodes embedded in the story graph
- A block represents a small logical chunk of content, usually separated by choices
- Block nodes are linked to other blocks by actions, redirections (prior to content generation), and continues (post content generation)
- Blocks may contain smaller 'micro-block' content fragments, like dialog, choices, or media
- Connections may be dynamically generated by filter (menu blocks)
- Scenes may have indirect connections to actors (via roles) and places (via locations), attaching specific actor or place instances to a scene via reference, filter, or creation is called "casting roles" or "scouting locations"

**Actor**
- An actor is a story node that can be attached to multiple scene roles or locations (indirect connections)
- Actors can delegate to several types of specialized child components for different features such as a demographic profile, look, or outfit

**Place**
- A place represents a fixed setting for multiple possible scenes
- Places/locations are implemented using the same interface as actors/roles

**Asset**
- An asset-singleton represents an immutable noun in the story world, for example, a sword or some gold
- Asset-singletons are considered "fungible", they are counted and stored in a wallet that can be managed by a specialized fungible trade handler
- Stateful assets (wrapped singleton nodes), asset-roles (a retainer), and asset-locations (an ownable castle) are managed by the association/trade handler
- Badges are asset-singletons that are assigned and unassigned dynamically based on conditions

**World**
- A world is a singleton story node that serves as a factory for new stories
- The world holds a story's script, template manager, media resource manager, asset manager, and a world-specific handler strategy registry
- All stories keep a reference to their world
- World public api: `get world info`, `get world list`, `get world media`
- World client api: `create story`
- World dev api: `get scene list`


Content
-------
Related to ingesting story scripts or generating story output

**Script Manager**
- Pydantic models for all story node types and integrated story script
- Script manager holds a script and metadata for a given world, can feed entity template data to a world for creating a new story
- Script manager can be modified to accept alternative script models or types (markdown, for example)

**Story Journal**
- Ordered list of content generated during story traversal
- Entries indexed at each user interaction

**Narrative Handlers**
- Narrative creators (updating/creating text to match scene state and character traits using generative AI and/or NLP/regex)
- Dialog micro-blocks (attach actor, attitude to each statement)
- Language tools

**Media Handlers**
- Media connector nodes (connects story node to media resource)
- Media resource manager
- Media creators (updating/creating media to match scene state and character traits using generative AI and/or svg assemblies)
- Staging micro-blocks (attach media transition, position to audio cues)


Mechanics
---------
Extensions for specific types of interesting narrative constructs, such as games or sandbox behaviors

**Actor extensions**
- Demographic profile (default names, origin, age, body swapping)
- Look (describe actor physical traits, create avatar media)
- Outfit (describe wearable assets, remove/wear actions)
- Ornaments (describe piercings, tattoos, etc.)

**Games**
- Game entities and move handler
- Interactive challenge blocks

**Sandboxes**
- Location maps
- Scheduled and localized events
- Mobile actors

**Stats**
- Stat domains and ranks
- Stat tests (cost, difficulty, reward)
- Situational effects (update tags, bonus/malus)
- Activity (stat test) blocks


Content
-------
Related to ingesting story scripts or generating story output

**Script Manager**
- Pydantic models for all story node types and integrated story script
- Script manager holds a script and metadata for a given world, can feed entity template data to a world for creating a new story
- Script manager can be modified to accept alternative script models or types (markdown, for example)

**Story Journal**
- Ordered list of content generated during story traversal
- Entries indexed at each user interaction

**Narrative Handlers**
- Narrative creators (updating/creating text to match scene state and character traits using generative AI and/or NLP/regex)
- Dialog micro-blocks (attach actor, attitude to each statement)
- Language tools

**Media Handlers**
- Media connector nodes (connects story node to media resource)
- Media resource manager
- Media creators (updating/creating media to match scene state and character traits using generative AI and/or svg assemblies)
- Staging micro-blocks (attach media transition, position to audio cues)


Mechanics
---------
Extensions for specific types of interesting narrative constructs, such as games or sandbox behaviors

**Actor extensions**
- Demographic profile (default names, origin, age, body swapping)
- Look (describe actor physical traits, create avatar media)
- Outfit (describe wearable assets, remove/wear actions)
- Ornaments (describe piercings, tattoos, etc.)

**Games**
- Game entities and move handler
- Interactive challenge blocks

**Sandboxes**
- Location maps
- Scheduled and localized events
- Mobile actors

**Stats**
- Stat domains and ranks
- Stat tests (cost, difficulty, reward)
- Situational effects (update tags, bonus/malus)
- Activity (stat test) blocks
