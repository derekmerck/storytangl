StoryTangl - Project Mission (v3.2)
===================================

## Overview

**Tangl** is a framework for designing, storing, and executing **interactive narratives** as **abstract story graphs**. It separates concerns into four main layers—**data**, **business**, **service**, and **presentation**—to handle everything from persistent storage and user management to story logic and multi-format rendering. This modular design supports scenarios ranging from **classic CYOA** branching to **open-world RPG** structures with concurrency, dynamic node creation, skill checks, and more.

---

## 4-Layer Application Stack

### 1. Data Layer

- **Responsibility**: Persisting all story state (graph nodes, edges, user data, version histories) in a robust, flexible manner.  
- **Goal**: Keep the **business layer stateless** by externalizing serialization and storage, so stories, user info, and logs/journals can be reloaded or shared among users or sessions.  
- **Entities to Serialize**:
  1. **ASG State** (the Abstract Story Graph, including dynamic nodes, references, and changes),  
  2. **User Data** (achievements, authorization, multi-story stats),  
  3. **Undo/Redo History** or version control diffs/snapshots,  
  4. **Story Journal** (the generated text, media references, or “timeline” of events as the user navigates the story).

### 2. Business Layer

- **Responsibility**: Implements the **core logic** of story management, graph traversal, condition checks, effect application, and hooking.  
- **Sub-Layers (the “3 cores”)**:
  1. **Source Content & Scripting** – Takes user-friendly definitions (YAML, DSL, Python modules, etc.) and compiles them into the internal ASG templates.  
  2. **State Representation & Management** – Maintains the “live” Abstract Narrative Graph (ANG) instance. This includes dynamic node creation, concurrency logic, hooking, and condition/effect resolution.  
  3. **Narrative & Media Output** – Generates, assembles, and tracks the final text/media “fragments” (the **journal**). The story “collapses” from possible paths to a single user-experienced sequence.

In essence, the **business layer**:

- **Manages the ASG**: The typed nodes/edges, hooking system, scoping of variables, plus concurrency or branching.  
- **Handles** node entry, condition checks, effects, and building the user’s “journal.”  
- **Remains “media-agnostic”**: Leaves final rendering details (fonts, colors, image placement) to the **presentation layer**.

### 3. Service Layer

- **Responsibility**: Exposes **RESTful** or **federated** APIs that front-end clients can call.  
- **Typical API Endpoints**:
  - **Story Interaction**: retrieving the current journal, posting a choice or action, or getting partial state info like a map or summary.  
  - **Account Management**: user login, user achievements, creating/deleting stories, etc.  
  - **System Features**: listing available story worlds, loading new modules, distributing or federating content-generation tasks.

The **service layer** allows multiple front-end clients (CLI, web, or an engine plugin) to interact with the same story logic seamlessly.

### 4. Presentation Layer

- **Responsibility**: Displaying the story to the end-user in a device-appropriate format. Could be:
  - A **CLI** with minimal media handling,  
  - A **Web Interface** that supports images, color-coded text, or dynamic layouts,  
  - A **Ren’Py** or other game engine plugin, etc.

Because **tANGL** defers exact rendering logic to the **presentation layer**, it can “negotiate” capabilities (like whether to show an image or fallback to text) at runtime without changing the underlying story logic.

---

## Abstract Story Graph (ASG)

At the heart of **tANGL** is the **Abstract Story Graph**, a **typed, directed** structure representing all possible story states and transitions:

### Node Types

1. **Scenes (Acts)** – Traversable narrative points. Contains sub-elements (“blocks”), branching logic, conditions/effects, and user choices.  
2. **Actors (Characters)** – Reusable entities that can appear in multiple scenes, carrying stats, inventories, or relationships.  
3. **Places (Settings)** – Locations or environments. Scenes link to places as “locations,” which can be swapped or reused across different arcs.  
4. **Assets (Objects / Props)** – Items or resources, potentially countable (like gold) or unique (like “the cursed sword”).

### Edges and Relationships

1. **Components / Children** – Hierarchical sub-structures (e.g., scene blocks, outfit items).  
2. **Indirect Links** – “Role” or “location” references that connect actors or places to scenes.  
3. **Traversable Paths** – The edges that represent the user’s navigable route from scene to scene (with conditions, skill checks, or branching).

**Scoped Context**: When traversing a scene node, the engine gathers context from parent scenes, global story variables, user data, etc. This scoping ensures **local variables** inherit from broader contexts while still enabling overrides or expansions in deeper blocks.

---

## Core Narrative Management

When the user (or an AI “navigator”) moves the “cursor” to a scene node:

1. **Check Redirects** – The node might auto-forward to another node.  
2. **Gather Context** – Collect parent scopes, global story state, user data.  
3. **Check Conditions** – Evaluate whether the node is available. If not, the story might branch or block the traversal.  
4. **Apply Effects** – Update stats, inventory, or relationships if the node is successfully entered.  
5. **Render Content** – Generate text and media fragments to append to the “journal.”  
6. **Check Continuations** – If the node offers choices or auto-transitions, guide the user or system to the next node.

The **journal** is the linear record of everything that’s “collapsed” from the possible story graph. Each new node entry appends fragments (text, images, etc.) to the journal. The data layer persists this so it can be undone, redone, or branched.

---

## Data and Serialization

Because stories can be large, **dynamic**, and multi-user:

- **Everything is stored as graph nodes** referencing one another by ID (including the user object, story history, journal entries).  
- **Undo/Redo** can be handled via snapshot or diff-based versioning of the node registry.  
- **User Data** (achievements, cross-story progress) can be stored in a global or per-user node, letting multiple stories share references.  
- **Stateless Service** approach means you load the relevant story graph from the data layer on each request, update it, and serialize changes back.

---

## Hooks and Plugins

A **critical** aspect of **tANGL** is allowing authors (or advanced designers) to inject **custom logic** at many points:

- **Compile/Load Hooks** – Before or after the DSL is parsed and turned into an ASG template.  
- **Graph Creation** – On new story instance or node creation, possibly randomizing stats or pulling from external data.  
- **Traversal Hooks** – On node entry, effect evaluation, condition checks, or final rendering steps.  
- **Serialization Hooks** – On save/load for custom fields or data transformations.

These **hooks** support new node types, advanced validations, AI-based generation, or specialized behaviors (like skill checks or day/night cycles). The **Python reference** implementation might allow decorators to register these hook functions, specifying priorities and how they override or augment normal pipeline steps.

---

## Service Interaction

Clients (CLI, web, or others) typically:

1. **Read** the current story journal to see what has happened so far.  
2. **Submit a choice or action**, which triggers the business layer to move the narrative cursor, apply logic, and generate new fragments.  
3. **Request** metadata (map of the world, summary of open quests) or updates (like available new arcs).  
4. **Manage** accounts and user sessions (start a new story, load an old one, handle cross-story achievements).

The service layer may also **federate** tasks to external microservices (like a generative AI service that creates images or extra text snippets on demand).

---

## Putting It All Together

1. **Author** defines a world via YAML/DSL plus Python (or other language) hooks.  
2. **Engine** compiles this into a robust **Abstract Story Graph** template.  
3. **When a user starts** the story, the engine clones/instantiates the graph (optionally spawning more dynamic nodes).  
4. **As the user navigates**:
   - Conditions are checked, effects applied, and text/media appended to the “journal.”  
   - The data layer logs each version for undo/redo or alternate branching.  
5. **Presentation** (CLI, web, etc.) fetches the updated journal and user progress, displaying it with appropriate style or media.  
6. **Hooks** can intercept or enhance each step—like injecting new subquests, performing custom validations, or calling AI generation.

**tANGL** thus provides a **unifying framework** for complex interactive narratives, supporting everything from short linear tales to large sandbox RPGs with concurrency, **modular expansions**, dynamic node creation, advanced branching, multi-user collaboration, or AI-driven plot expansions. By **cleanly separating** the data (storage), business (logic), and presentation (front-end) concerns, **tANGL** remains **highly extensible** and capable of evolving with new technologies and authoring paradigms.