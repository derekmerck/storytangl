StoryTangl Package Organization
===============================

Follows a distinct 4-layer architecture:

- General: `core`, `utilities`
- Data Layer: `persistence`
- Business Logic: `story`, `world`, `mechanics`, `media`, `narrative`
- Service Layer: `persistence`, `service`, `system`, `user`
- Presentation Layer: separate apps packages (`cli`, `rest`)

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

Algorithm modules with no deps on other subpackages

**deps**: None

Business
========

Story
-----

Entity specialization for the 3-layer abstract narrative graph and associated handlers.

- **`concept`** -> general links within and from structure, narrative concepts like `actor`, `place`, `prop`, `landmark`, `achievement`, `relationship` and linking structures
- **`journal`** and **`journal.content_fragment`** -> list links within, general links to originating structure nodes and thence transitively to concepts, realized linear output of story to current state
- **`structure`** -> deps on `concept`, `journal`, traversable links within, general links from concept, to journal, navigable plot points like `scene`, `block`, `action` that mediate between concepts and realized story content

- **`story node`** -> base class for concept, structure, and journal nodes
- **`story graph`** -> a graph with concept, structure, and journal layers
- **`player`** -> specialized story node for reader proxy that can attach managers like an actor (inventory, relationships, outfit, etc.)

- **`story api`** -> deps: `service.api_endpoint`, api for story endpoints: `get journal`, `follow edge`, `get story info`, and story dev endpoints: `check_condition`, `apply effect`, `get node info`, `goto node`

**deps**: `core`

Media
-----

Handlers for converting structure nodes into media records at init, traversal and for converting media records into media content fragments upon access

- **`media record`**
- **`media registry`**

- **`image creators`** -> creation services like stable diffusion or svg paperdolls
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

Worlds can publish mechanics for other worlds by installing them in the mechanics namespace.

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

