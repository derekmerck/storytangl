# StoryTangl v3.7

[![CI](https://github.com/derekmerck/storytangl/actions/workflows/ci.yml/badge.svg)](https://github.com/derekmerck/storytangl/actions/workflows/ci.yml)

**TanglDev, Spring 2026**  

## Overview

StoryTangl is an interactive storytelling engine for creating, hosting, and playing
dynamic, interactive narrative experiences. It is designed to support a wide range 
of storytelling styles, from simple branching narratives to complex, state-driven
worlds with dynamically generated content. It is capable of concurrently handling
multiple story worlds and multiple users.

The framework is thoroughly documented with `Sphinx`, and documentation is
accessible on [ReadTheDocs](https://readthedocs.org/projects/StoryTangl). This
includes both story-author and developer guides, as well as the OpenApi specification
for the REST API server.

**The Tangl Abstract Narrative Graph Library for Interactive Stories**, inspired by morphological shape models, compiler theory, superposition, Kantian categoricals, and a weaving metaphor.

StoryTangl aims to **separate** the concerns of narrative structure, story content, stateful navigation, and final presentation. By **representing stories** as an abstract graph that “collapses” into a linear narrative under user or system choices, it supports traditional linear novels, branching CYOAs, sandbox RPGs, and more.

---

## Usage

### Single Story App

Use Tangl to:

1. **Load** a single story definition from a `tangldown` script (Markdown+YAML) or other source.  
2. **Compile** a story definition into an intermediate representation or “story world.”  
3. **Create** a story instance (graph) from that world to track reader navigation and state.  
4. **Navigate** or "play" a story line as a user, by picking branches or letting the system auto-select algorithmically.  
5. **Render** the final text (or images/audio) to a CLI, a web page, or any other medium.

### Multi-World Server

At scale, Tangl can be hosted as a **multi-world server**:

1. **Serve** many distinct story worlds simultaneously (for different authors or game modules).  
2. **Manage** multiple user sessions, each with its own story instance.  
3. **Coordinate** real-time branching or updates if desired (cooperative narratives, analytics on user paths, etc.).  
4. **Expose** a REST or GraphQL API for remote clients, from web front-ends to game engines like Unity or Ren’Py.

---


## Usage

### Install with `pip`

Install and run a tangl story server on port 8000.
```bash
$ pip install storytangl
$ tangl-serve
```
or run a story from the command-line interface (CLI).
```bash
$ tangl-cli
```

(Currently distributing on PyPI-testing.)

### From source

Requires `git+lfs` and `poetry`.

```bash
$ git clone https://github.com/tangldev/storytangl
$ cd storytangl
$ git lfs pull
$ pip install poetry
$ poetry install --only main
$ tangl-serve
```

### Keep the docs green

StoryTangl ships with a pre-commit hook that builds the Sphinx documentation
whenever you touch files that affect the docs. Enable it once per clone and make
sure the docs dependencies are available:

```bash
$ git config core.hooksPath .githooks
$ poetry install --with docs
```

You can always trigger the same check manually with `poetry run sphinx-build -b html docs/source docs/_build/html`.

### Docker

The git repo includes a Dockerfile for the reference app that can be used as
a quick-start on a PAAS environment.

```bash
$ docker build . -t storytangl:4
$ docker run -p 8000:8000 storytangl:4
```


---

## Design Concepts

Tangl organizes narrative into **four conceptual layers**, ensuring each part remains loosely coupled and extensible:

1. **Story World**  
   - *“Domain of Possibility”*  
   - Houses the **templates**, **logic**, and **constraints** that shape a potential narrative.  
   - In morphological terms, it’s the “shape model” or blueprint for what can exist or happen in the story universe.

2. **Story Graph (ANG)**  
   - *“Semantic Instance”*  
   - A mesh of specific narrative concepts: nodes (scenes, characters, items) and edges (relationships, triggers).  
   - Tracks constraints, branching logic, and the internal state (e.g., “if X is dead, Y cannot occur”).  
   - In Kantian analogy, this is the “noumenal narrative”, the story’s underlying reality before we present it to the user.

3. **Story Navigator**  
   - *“Collapser”*  
   - Traverses the graph to produce a *particular* sequence of events.  
   - Manages user choices or algorithmic logic (e.g., BFS, backtracking, randomized exploration).  
   - Can allow undo/redo or keep multiple parallel lines.

4. **Story Representer**  
   - *“Phenomenon” / Presentation Layer*  
   - Converts the evolving story line into concrete output: text, images, audio, VR scenes, etc.  
   - Applies any runtime transformations (e.g., substituting pronouns, generating final phrasing).  
   - Ensures the user sees or hears a consistent experience based on the underlying story state.

By **keeping these layers distinct**, we can ingest a single “semantic core” of a story and project it into many forms like weaving different cloth patterns from the same thread.

---

## Transformation Pipeline

1. **Source Input**  
   - Authors write a “Storydown” script or import from other CYOA engines.  
   - Can combine **free-form** narrative with **structured** metadata (like constraints, entity references).

2. **Parsing & Compilation**  
   - A parser translates the source into an **Intermediate Representation** (templates, constraints, events).  
   - *(Optional)* **LLM-Assisted** checks can fill or suggest missing details.

3. **Intermediate Representation → ANG**  
   - Construct or refine the **Abstract Narrative Graph** (ANG), specifying possible branches, constraints, and logic.

4. **Story Instance**  
   - When a user starts a session, Tangl creates a unique *instance* of the ANG, complete with local state and branching possibilities.

5. **Presentation Generation**  
   - The system *renders* or *generates* final media based on the chosen path.  
   - Might fetch assets (images, SFX) or run text transformations (pronoun changes, style tweaks).

6. **Runtime Interaction**  
   - Users make choices; Tangl updates the graph state (inventory changes, character statuses, etc.).  
   - The story “collapses” further with each decision, leading to unique or recurring arcs.

7. **Client Loop**  
   - **Get** current story content (narrative text, media, interactive options).  
   - **Display** content to the user (CLI, web, VR, etc.).  
   - **Post** the user’s choice/input.  
   - **Repeat** until an ending or user exit.

---

## Basic Models & API

### Story World

- **Definition**: The domain of all potential narrative elements, constraints, and logic rules.  
- **Implementation**: YAML/JSON files, a database, or a DSL like Storydown.  
- **Key Functions**:
  - `compile_world`: Load and compile the world definition into an intermediate representation.  
  - `create_story`: Instantiate a new **story graph** from the world’s templates and rules.  
  - `hook_event`: Register callbacks for model updates, navigation triggers, or representation events.

### Story Graph (ANG)

- **Definition**: The “Abstract Narrative Graph” that holds **scenes**, **characters**, **objects**, **relationships**, etc.  
- **Tracks**: Constraints, triggers, visited nodes, user states.  
- **Key Functions**:
  - `init_story`: Initialize or reset a story instance.  
  - `update_story`: Apply changes to the story (e.g., a user’s action or an automated event).  
  - `update_story_node`: Modify a particular node (scene) or relationship.

#### Navigator

- **Manages**: Branching, path selection, undo/redo functionality.  
- **Key Methods**:
  - `get_choices`: Returns the available transitions or actions from the current state.  
  - `do_choice`: Applies a chosen transition, updating the story and firing relevant events.  
  - `get_history`: Returns the path or branching log of visited states.  
  - `undo` / `redo`: Revisits prior states if allowed.

### Representer

- **Handles**: Rendering or transforming the story line into **user-facing output** (text, visuals, etc.).  
- **Key Methods**:
  - `get_story_line`: Fetch the collection of “fragments” (narrative text, media references) for the current step.  
  - `resolve_story_line`: Generate or finalize the textual/media content for a scene based on the user’s state.  
  - `branch_story_line`: Optionally create parallel “views” or partial replays.

### Serializer

- **Handles**: Persistence for story graphs, so they can be saved/loaded.  
- **Key Methods**:
  - `load_story`: Load a serialized instance from disk or DB.  
  - `save_story`: Save the current state for resumption or analytics.

---

## Writing in tangldown

*(Placeholder for future examples)*  
Tangl supports a **Markdown+YAML** hybrid DSL called **tangldown**, allowing authors to mix normal prose with embedded metadata. Example:

`````markdown
# Scene: The Tavern

```yaml
id: scene_tavern
characters: [Aria, Bartender]
constraints:
  - aria_has_gold: true
```

Aria steps into the dimly lit tavern...
`````

The parser turns this into a **story world** definition, which you can compile, instantiate, and navigate.  A smart parser will even make simple inferences, like the scene ids, characters, and settings directly from a content block's tags and text content.

---

## Further Thoughts

### Roles

1. **Author**  
   - Creates the **story world** and sets overarching constraints. In a linear novel, the author also navigates a single path in advance.

2. **Navigator**  
   - Chooses or algorithmically determines the path. In classical CYOA, the user picks branches. In a more automated scenario, an AI or a set of heuristics might do so.

3. **Reader**  
   - Consumes the final rendered story. In purely linear works, the reader has no branching power. In interactive works, the reader effectively *is* the navigator.

### Latent Story Space

- The story world can be viewed as a **wavefunction** of all possible outcomes— “superpositions” of potential arcs and endings.  
- Each user choice **collapses** this wavefunction, producing a single realized path. Unexplored branches remain latent, awaiting new playthroughs.

### Use Cases & Scaling

- **Linear or Single-Path**: Straightforward compilation yields an ebook-like or static website.  
- **Classic CYOA**: Handcrafted branching for discrete forks, each leading to unique outcomes.  
- **Sandbox RPG**: Large dynamic graph with side quests, concurrency, and advanced state logic. Possibly uses procedural generation for expansions.

### Future Features

1. **Collaboration & Multi-User**  
   - Real-time branching or co-authoring in shared story worlds.

2. **Analytics & Telemetry**  
   - Track user choices, measure path popularity, gather analytics for authors.

3. **AI-Driven Plot Generation**  
   - Dynamically generate or refine subplots, side quests, and characters under author-approved constraints.

4. **Cross-Story “Meta-State”**  
   - Link achievements or states across multiple story instances; e.g., finishing one arc unlocks special branches in another.

---

## Contributing

We welcome feedback, bug reports, and feature requests. For more advanced usage details and code examples, see our [Documentation](#). 

---

**Tangl** strives to offer a **unifying framework** for interactive fiction—where authors can craft intricate branching worlds, and readers can explore or shape them in multiple formats. By **weaving** the threads of structure, semantics, state navigation, and final presentation, Tangl aspires to push narrative design into new dimensions.


## Modding

Any game world can be 'modded' by registering new plugins or media locations
with the game world manager.  

Media that follows the world's default naming convention will be selected 
preferentially.  The main game engine includes hooks to various key features 
like game initialization and turn advancement.  Each game-world has its own
sandboxed plugin-manager.

## Development

We use Git and Git-LFS for source and basic media version control and 
collaboration.

The unit-test-suite targets 85% coverage.  We utilize `pytest` as our testing
framework, and tests run automatically on every commit to the main branch.

## License

MIT except BSD on the Demographics module name-banks, which includes content
directly lifted from a BSD-licensed project, see that subpackage for details.
