StoryTangl Package Organization
===============================

Uses a separated-concern, layered architecture:

- General: `core`, `utilities`
- Data Layer: `persistence`
- Business Logic: `story`, `world`, `mechanics`, `media`, `narrative`
- Service Layer: `persistence`, `service`, `system`, `user`
- Presentation Layer: apps packages in separate source tree (`cli`, `rest`)
- World Data: plugins and resources in separate source trees

General
=======

Core
----

Basic managed data structures used throughout the code.

- **`entity`** -> basic managed `entity`, `registry`, `singleton`
- **`graph`** -> connectable entities `node`, `edge`, and `graph`, wrapped `singleton node`
- **`handlers`** -> general entity task pipeline and specific implementations for gathering context, and contextually scoped tasks like rendering, conditional evaluation, applying effects, handling dynamic associations, and edge traversal

**deps**: None

Utils
--------------

Namespace subpackage with algorithm modules with no deps on other subpackages.

Worlds can share utilities with other subpackages by installing them in the `utils` namespace.

**deps**: None

Business
========

Story
-----

Entity specialization for the 3-layer abstract narrative graph and associated handlers.

- **`concept`** -> general links within and from structure nodes; narrative concepts like `actor`, `place`, `prop`, `landmark`, `achievement`, `relationship` and linking structures
- **`journal`** and **`journal.content_fragment`** -> list links within; general links to originating structure nodes and thence transitively to concepts, realized linear output of story to current state
- **`structure`** -> deps on `concept`, `journal`; traversable links within; general links from concept, to journal, navigable plot points like `scene`, `block`, `action` that mediate between concepts and realized story content

- **`story node`** -> base class for concept, structure, and journal nodes
- **`story graph`** -> a graph with concept, structure, and journal layers
- **`player`** -> specialized concept node for reader proxy that can attach managers like an actor (inventory, relationships, outfit, etc.)

- **`story api`** -> deps: `service.api_endpoint`, api for story endpoints: `get journal`, `follow edge`, `get story info`, and story dev endpoints: `check_condition`, `apply effect`, `get node info`, `goto node`

**deps**: `core`

Media
-----

Handlers for converting structure nodes into media records at init, traversal and for converting media records into media content fragments upon access

- **`media record`**
- **`media registry`**

- **`image creators`** -> creation services like stable diffusion, svg paperdolls, playing card backs and faces
- **`audio creators`**

- **`media api`**: deps: `service.api_endpoint`, api for media endpoints: `add media record`, `get media record`,  `resolve media record`, `get media service info` (for publishing services)

**deps**: `story`

Narrative
---------

Handlers for converting structure nodes into narrative content fragments at init, traversal, or client request

- **`lang`** -> utilities, no dependencies on other subpackages, utilities for english language parsing and generation, e.g. wrappers for spacy, nltk, conjugation scripts
- **`text creators`** -> services like jinja templates, style, vocabulary, named entity id and replacement, etc.
- **`dialog creators`** -> specialized parser for text content with dialog

**deps**: `story`

Mechanics
---------

Namespace subpackage for complex concepts with structure nodes that wrap them as components, such as `stat` and `stat challenge block`, `interactive game` and `game block`, actor `look` and `outfit` add-ons.

Worlds or plugins can share mechanics globally by installing them in the `tangl.mechanics` namespace.

**deps**: `story`

World
-----

Singleton domain manager for story scripts, assets, subclasses and handler plugins, create new story graphs

- **`prop manager`** -> domain specific singletons
- **`script manager`** -> domain specific templates for new stories, may require `journal.content_fragment`
- **`pipeline manager`** -> domain specific handlers for pipelines

- **`world api`**:  deps: `service.api_endpoint`, api for world endpoints: `load world`, `new story`, `get world info`

**deps**: `core`

Service
=======

Service
-------

Business handlers that will be exposed by the service layer depend on `service.api_endpoint` for annotation decorator

- **`api endpoint`** -> decorator wraps story, world, user, system handlers
- **`service manager`** -> provides automatic service object with integrated persistence and user manager

**deps**: None

User
----

Service layer entity that manages collections of stories for tracking stats and achievements.

- **`user api`**:  api for user endpoints: `new user`, `update user`, `get user info`

**deps**: `core`

System
--------------

Provides basic info -- uptime, version, etc.

- **`system api`**:  api for system endpoints: `get system info`

**deps**: None

Persistence
--------------

- Generic data layer structuring and unstructuring for dataclass-type instances.
- Flexible persistence backends using a unified dictionary get/put api.

**deps**: None


Working File Tree
=================

```
.
|-- core
|   |-- entity
|   |   |-- __init__.py
|   |   |-- entity.py
|   |   |-- inheriting_singleton.py
|   |   |-- registry.py
|   |   `-- singleton.py
|   |-- graph
|   |   |-- __init__.py
|   |   |-- dynamic_edge.py
|   |   |-- graph.py
|   |   `-- singleton_node.py
|   |-- handlers
|   |   |-- entity_handlers
|   |   |   |-- __init__.py
|   |   |   |-- availability.py
|   |   |   |-- has_context.py
|   |   |   |-- initialization.py
|   |   |   |-- renderable.py
|   |   |   |-- runtime.py
|   |   |   `-- templated_defaults.py
|   |   |-- graph_handlers
|   |   |   |-- __init__.py
|   |   |   |-- associating.py
|   |   |   |-- has_traversal_history.py
|   |   |   `-- traversable.py
|   |   |-- __init__.py
|   |   |-- task_handler.py
|   |   `-- task_pipeline.py
|   `-- __init__.py
|-- mechanics
|   |-- character
|   |   |-- __init__.py
|   |   |-- enums.py
|   |   |-- look.py
|   |   |-- ornaments.py
|   |   `-- outfit.py
|   |-- collection
|   |   |-- bag
|   |   |   `-- __init__.py
|   |   |-- slots
|   |   |   `-- __init__.py
|   |   |-- __init__.py
|   |   `-- notes.md
|   |-- game
|   |   |-- __init__.py
|   |   |-- game_block.py
|   |   `-- notes.md
|   |-- sandbox
|   |   |-- __init__.py
|   |   `-- sandbox.py
|   `-- stats
|       |-- challenge
|       |   |-- __init__.py
|       |   |-- challenge_block.py
|       |   `-- opinionated_stats.py
|       |-- __init__.py
|       |-- notes.md
|       `-- quantized_value.py
|-- media
|   |-- media_creators
|   |   |-- raster_forge
|   |   |   `-- __init__.py
|   |   |-- stable_forge
|   |   |   `-- __init__.py
|   |   `-- svg_forge
|   |       `-- __init__.py
|   |-- __init__.py
|   |-- media_controller.py
|   |-- media_data_type.py
|   |-- media_record.py
|   `-- media_registry.py
|-- narrative
|   |-- narrative_creators
|   |   |-- chat_forge
|   |   |   `-- __init__.py
|   |   |-- dialog_parser
|   |   |   `-- __init__.py
|   |   `-- __init__.py
|   `-- __init__.py
|-- persistence
|   |-- storage
|   |   |-- __init__.py
|   |   |-- file_storage.py
|   |   |-- in_memory_storage.py
|   |   |-- mongo_storage.py
|   |   |-- protocol.py
|   |   `-- redis_storage.py
|   |-- __init__.py
|   |-- factory.py
|   |-- manager.py
|   |-- serializers.py
|   `-- structuring.py
|-- service
|   |-- __init__.py
|   |-- api_endpoint.py
|   `-- service_manager.py
|-- story
|   |-- concept
|   |   |-- actor
|   |   |   |-- __init__.py
|   |   |   |-- actor.py
|   |   |   `-- role.py
|   |   |-- asset
|   |   |   |-- __init__.py
|   |   |   |-- asset.py
|   |   |   |-- badge.py
|   |   |   |-- countable_asset.py
|   |   |   `-- discrete_asset.py
|   |   |-- place
|   |   |   |-- __init__.py
|   |   |   |-- location.py
|   |   |   `-- place.py
|   |   |-- __init__.py
|   |   |-- achievement.py
|   |   |-- concept_node.py
|   |   `-- landmark.py
|   |-- journal
|   |   |-- content_fragment
|   |   |   |-- __init__.py
|   |   |   |-- content_fragment.py
|   |   |   |-- group_fragment.py
|   |   |   |-- kv_fragment.py
|   |   |   |-- media_fragment.py
|   |   |   |-- presentation_hints.py
|   |   |   |-- text_fragment.py
|   |   |   `-- user_event_fragment.py
|   |   |-- __init__.py
|   |   |-- has_journal.py
|   |   `-- journal_controller.py
|   |-- structure
|   |   |-- __init__.py
|   |   |-- action.py
|   |   |-- block.py
|   |   |-- menu_block.py
|   |   |-- plot_controller.py
|   |   `-- scene.py
|   |-- __init__.py
|   |-- story_controller.py
|   |-- story_graph.py
|   `-- story_node.py
|-- system
|   |-- __init__.py
|   |-- system_controller.py
|   `-- system_info.py
|-- user
|   |-- __init__.py
|   |-- achievement.py
|   |-- user.py
|   `-- user_controller.py
|-- utils
|   |-- app_uptime.py
|   |-- bookmarked_list.py
|   |-- dereference_obj_cls.py
|   |-- enum_plus.py
|   |-- file_check_values.py
|   |-- get_code_name.py
|   |-- is_valid_uuid.py
|   |-- load_yaml_resource.py
|   |-- pixel_avg_hash.py
|   |-- rejinja.py
|   |-- safe_builtins.py
|   |-- setup_yaml.py
|   `-- shelved2.py
|-- world
|   |-- script_manager
|   |   `-- __init__.py
|   |-- __init__.py
|   |-- asset_manager.py
|   |-- plugin_manager.py
|   |-- world.py
|   `-- world_controller.py
|-- config.py
|-- defaults.toml
|-- info.py
`-- type_hints.py
```