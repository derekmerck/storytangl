# StoryTangl v3.7

**TanglDev, Fall 2025**  

[![CI](https://github.com/derekmerck/storytangl/actions/workflows/ci.yml/badge.svg)](https://github.com/derekmerck/storytangl/actions/workflows/ci.yml)

**A graph-based narrative engine for interactive storytelling**

---

## What This Is

StoryTangl is a **reference implementation** of a sophisticated graph-based narrative system. It demonstrates a novel architecture where stories exist as abstract graphs that "collapse" into linear narratives through player choices—think quantum superposition for interactive fiction.

### Project Status

StoryTangl is an actively developed reference implementation. The core architecture is stable and exercised across the test suite, but individual subsystems are at varying levels of completeness and are expected to evolve.

**Core capabilities:**
- Layered architecture across core, IR, journal, VM, story, service, and apps
- Event-sourced execution with ledger persistence
- Multi-phase VM pipeline with deterministic resolution
- Planning & provisioning system for dynamic narrative construction
- YAML-based story scripting with validation
- Linear and branching narrative playback via CLI and REST API
- Multiple persistence backends (in-memory, file, Redis, MongoDB, SQLite)
- Vue 3 web client with a functional MVP UI
- Test suite with pytest and coverage reporting
- Detailed API documentation with Sphinx

**Active areas of work:**
- Refining story dispatch integration into the VM pipeline
- Role and setting provisioning driven from story scripts
- Media provisioning and client-facing media contracts
- Tunable narrative voices, vocabularies, languages
- Comprehensive reference stories and user/author guide

**Future directions:**
- Dynamic and generative media integration
- Turnkey RPG and sandbox mechanics (progression, maps, schedules, mobile actors, etc.)
- Multi-reader stories
- Transpilers and adapters to/from other narrative engines
- Continuous narrative interpolation rather than sampled points
- Specialized in-story asset types (inventory, wearables, etc.)
- Constraint satisfaction with SAT solver

---

## Architecture Highlights

StoryTangl's distinguishing features come from its architectural choices:

### Clean Layering
```
core     → Generic graph entities, registries, records
ir       → Script / DSL models (core/story/media/vm IR)
journal  → Narrative fragments and discourse structures
vm       → Narrative virtual machine with phase-based execution
story    → Domain model (episodes, scenes, actors, locations)
service  → Orchestrator pattern with controller endpoints
apps     → CLI, REST API, web client
```

**Dependency flow is strictly one-way.** Lower layers never import from higher ones.

### Phase Bus Execution

The VM uses an eight-phase execution cycle for deterministic, auditable narrative resolution:

The VM uses a multi-phase execution cycle for deterministic, auditable narrative resolution. Phases are ordered, but not every step needs to perform work in every phase:

1. **INIT** – Initial placeholder before any work has run.
2. **VALIDATE** – Check preconditions for the current cursor and candidate transitions.
3. **PLANNING** – Resolve frontier dependencies and provision needed resources.
4. **PREREQS** – Run pre-transition hooks or prerequisite transitions.
5. **UPDATE** – Apply state changes to the graph and runtime entities.
6. **JOURNAL** – Generate narrative output fragments.
7. **FINALIZE** – Commit the frame as an event-sourced patch to the ledger.
8. **POSTREQS** – Run post-transition hooks and redirects (epilogues, follow-ups).

This separates concerns clearly: planning happens *before* choices are presented, preventing softlocks.

### Event Sourcing

Every narrative session is a **Ledger** consisting of snapshots + patches. This enables:
- Deterministic replay
- Efficient persistence
- Clear audit trail
- Time-travel debugging

### Dynamic Provisioning

The planning system can:
- Search for existing resources (actors, items, locations)
- Create new ones from templates
- Update existing resources
- Clone and modify resources

Requirements distinguish between hard dependencies (gates choice availability) and soft ones (nice-to-have).

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/derekmerck/storytangl.git
cd storytangl

# Install with Poetry
poetry install

# Or install specific extras
poetry install -E server  # Includes FastAPI, Redis, MongoDB
poetry install -E cli     # Just the command-line interface
```

### Run a Story (CLI)

```bash
# Start the interactive CLI
poetry run tangl-cli

# Or use the console script
tangl-cli

# In the CLI:
> load_script path/to/your_story.yaml
> create_story my_story
> story        # View current state
> do 1         # Make first choice
```

### Run a Story (API + Web)

```bash
# Start the REST API server
poetry run tangl-serve
# Or: uvicorn tangl.rest.main:app --reload

# In another terminal, start the web client
cd apps/web
yarn install
yarn dev
```

The web client will open at `http://localhost:5173` and connect to the API at `http://localhost:8000`.

### Docker Deployment

```bash
# Build the image
docker build -t storytangl:3.7 .

# Run the server (includes API + docs)
docker run -p 8000:8000 storytangl:3.7
# optionally mount an external 'worlds' directory with story content

# For the CLI instead, just override the entrypoint
docker run -it storytangl:3.7 tangl-cli
```

---

## Writing Stories

Stories are defined in YAML with a simple, expressive syntax:

```yaml
label: my_story
metadata:
  title: "My First Story"
  author: "Your Name"

scenes:
  intro:
    blocks:
      start:
        content: "Your adventure begins at a crossroads."
        actions:
          - text: "Take the left path"
            successor: left_path
          - text: "Take the right path"
            successor: right_path
      
      left_path:
        content: "You venture into the dark forest..."
        # More blocks here
      
      right_path:
        content: "You follow the sunny trail..."
        # More blocks here
```

### Script Features

**Currently Supported:**
- Hierarchical scene/block structure
- Multiple choice actions
- Inline content with Jinja2 templating
- Actor and location definitions
- Reusable templates
- Asset manifests (for media)

**In Development:**
- Role/setting requirements on scenes
- Conditional availability (guards)
- Dynamic provisioning from templates
- State-based content variations
- Markdown-like writerly format

See `engine/tests/resources/` for working examples.

---

## Development

### Architecture Philosophy

StoryTangl follows strict principles:

1. **Type purity**: Store data in native Python types (bytes for hashes, UUID objects, not strings). Serialize only at boundaries.

2. **Explicit mechanisms**: Small, clear functions over clever magic. Deterministic behavior.

3. **Test-driven**: Post-design test coverage. Use xfail markers for intended-but-unimplemented features.

4. **Layer discipline**: No upward imports. Core stays generic. Domain logic lives in higher layers.

5. **Reference implementation**: Prioritize correctness and clarity over performance. This is meant to be read and understood.

### Running Tests

```bash
# All tests
poetry run pytest

# Specific layers
poetry run pytest engine/tests/core
poetry run pytest engine/tests/vm
poetry run pytest engine/tests/story

# With coverage
poetry run pytest --cov=tangl --cov-report=html

# Watch mode
poetry run pytest --watch
```

### Documentation

```bash
# Build Sphinx docs
cd docs
poetry run make html

# View at docs/build/html/index.html
```

**Read these first:**
- `AGENTS.md` - Contributor guide with coding conventions
- `docs/source/contrib/` - Architecture and design patterns
- Design docs near relevant code (e.g., `engine/src/tangl/vm/provision/PLANNING_DESIGN.md`)

### Project Structure

```
storytangl/
├── engine/
│   ├── src/tangl/
│   │   ├── core/          # Graph entities, registries, records
│   │   ├── vm/            # Virtual machine, planning, ledger
│   │   ├── story/         # Domain model (episodes, actors, etc.)
│   │   ├── service/       # Orchestrator, controllers
│   │   ├── ir/            # Scripting/template models
│   │   ├── journal/       # Output stream models
│   │   └── persistence/   # Storage backends
│   └── tests/             # Comprehensive test suite
├── apps/
│   ├── cli/               # Command-line interface
│   ├── server/            # FastAPI REST API
│   └── web/               # Vue web client
├── docs/                  # Sphinx documentation
└── worlds/                # Reference story content
```

---

## Design Concepts

### Narrative as Quantum Collapse

StoryTangl treats narrative as a field of potentials. Story elements exist in *superposition*—they are possible but not yet real. Player choices cause *collapse*: specific scenes, characters, and events materialize while others remain forever unrealized.

This isn't just metaphor. The architecture literally implements:
- **Superposition**: Template nodes that can become multiple concrete instances
- **Observation**: The planning phase that resolves ambiguity
- **Collapse**: Deterministic materialization through the phase bus
- **Entanglement**: Dependency edges that link narrative elements

### Separation of Concerns

The system distinguishes four conceptual layers:

1. **Story World** (Domain of Possibility)
   - Templates, constraints, logic rules
   - The "shape model" of what *can* exist

2. **Story Graph** (Semantic Instance)
   - Specific narrative concepts: scenes, characters, relationships
   - State tracking and branching logic
   - The "noumenal narrative" before presentation

3. **Story Navigator** (Collapser)
   - Traverses graph to produce event sequences
   - Manages choices, planning, state updates
   - The execution engine

4. **Story Representer** (Phenomenon)
   - Converts abstract narrative into concrete output
   - Handles text rendering, media, formatting
   - What the player actually experiences

By keeping these separate, one semantic core can project into many forms—like weaving different patterns from the same thread.

### Compiler Metaphor

If you're a developer, think of StoryTangl as a narrative compiler:

- **YAML scripts** are the source language (author-friendly)
- **Graph representation** is the intermediate form (runtime-efficient)
- **VM phases** are the instruction set architecture
- **Journal fragments** are the execution trace
- **Planning system** is the optimizer (resolves dependencies ahead of time)

This framing makes the architecture immediately comprehensible to programmers.

---

## API Overview

### REST Endpoints

The FastAPI server provides a clean HTTP interface:

**World Management:**
- `GET /worlds` - List available story worlds
- `GET /worlds/{world_id}` - Get world metadata
- `POST /worlds/load` - Load world from script

**Story Operations:**
- `POST /story/create` - Start new story session
- `GET /story/update` - Get latest narrative state
- `POST /story/do` - Execute choice
- `GET /story/status` - Check session status
- `DELETE /story` - End session

**System:**
- `GET /health` - Health check
- `GET /openapi.json` - OpenAPI spec

See `/docs` endpoint when running the server for interactive API documentation.

The server app also bundles a simple media server for exposing world and system media objects to a story client.

### Python API

For direct integration:

```python
from uuid import UUID

from tangl.service.orchestrator import Orchestrator
from tangl.service.controllers.runtime_controller import RuntimeController
from tangl.service.controllers.world_controller import WorldController

# Initialize orchestrator and register controllers
orchestrator = Orchestrator()
orchestrator.register_controller(WorldController())
orchestrator.register_controller(RuntimeController())

user_id = UUID("00000000-0000-0000-0000-000000000000")  # Replace with a real user id

# Load a world
world_info = orchestrator.execute(
    "WorldController.load_world",
    user_id=user_id,
    source="path/to/story.yaml",
)

world_id = world_info.world_id

# Create story session
runtime = orchestrator.execute(
    "WorldController.create_story",
    user_id=user_id,
    world_id=world_id,
    story_label="session_001",
)

ledger_id = runtime.ledger_id

# Get current state
update = orchestrator.execute(
    "RuntimeController.get_story_update",
    user_id=user_id,
    ledger_id=ledger_id,
)

# Make choice
result = orchestrator.execute(
    "RuntimeController.do_action",
    user_id=user_id,
    ledger_id=ledger_id,
    action_id=update["choices"][0]["uid"],
)
```

The orchestrator handles all resource hydration and persistence automatically.

---

## Performance & Scale

**Current State:**
- Optimized for **correctness** over speed (reference implementation)
- Single-threaded execution within a user session
- Concurrent users/stories isolated via per-user locking
- Memory footprint scales with graph size + journal length

---

## Philosophical Foundations

### Why This Architecture?

This is a bit of navel-gazing, but this architecture has been 30 years in the making, drawing on _many_ intellectual traditions that I have learned about and engaged with over the decades.

**Kantian Framework:** The story graph is the "noumenal" reality (things-in-themselves), while rendered output is "phenomenal" (things-as-perceived). The VM mediates between these realms.

**Platonic Forms:** Templates are ideal forms; instances are shadows in the cave. The planning system is the mechanism for projecting forms into concrete existence.

**Compiler Theory:** YAML→Graph→Journal is a compilation pipeline with intermediate representations at each stage. The phase bus is an instruction set architecture for narrative execution.

**AI Planning (STRIPS):** Requirements specify preconditions; provisioners apply operators; the planning cycle searches the state space of possible narratives.

**Morphological Models:** The story world is a shape model defining the space of valid narratives. Story instances are specific shapes sampled from this space and projected into a representation space as they are unrolled.

And these aren't just weird analogies —- they are the actual design principles that shaped concrete technical choices and referenced in the logic.

### Evolution Through Iteration

This is version 3.7, representing the ~37th architectural iteration (4 rewrites with 8-12 iterations each over 5+ years).  Each rewrite has been driven by the evolution of key strategies.

1. **system and domain encapsulation** emerged after multiple  attempts at monolithic systems
2. **Phase bus** replaced brittle event handlers and task chains
3. **Event sourcing** solved replay and debugging problems
4. **Type purity** eliminated subtle serialization bugs
5. **Planning-first** prevents softlocks better than backtracking
6. **Template-driven** scales better than hardcoded content
7. **Interactions as re-entrant nodes** provide a powerful adjunct for embedding complex, procedurally driven subtrees

Each major version abandoned working code to get the architecture closer to correct. The current design is stable (for now) because it's been tested through repeated rebuilds.

---

## Contributing

If you want to contribute:

1. **Read `AGENTS.md` first** - Contains all coding conventions
2. **Study the layer boundaries** - Respect the architecture
3. **Write tests** - Use xfail for intended features
4. **Document thoroughly** - This is a reference implementation
5. **Ask questions** - Better to clarify than assume

### Key Conventions

- Python 3.13+ with type hints
- Pydantic for all data models
- pytest with comprehensive coverage
- Black-like formatting (4-space indent)
- Sphinx for documentation (reStructuredText in docstrings, Markdown/Myst for design guides)
- Keep lines under 100 characters

See `docs/source/contrib/coding_style.md` for detailed guidelines.

---

## License

MIT except BSD on the Demographics module name-banks, which includes content
directly lifted from a BSD-licensed project, see that subpackage for details.

---

## Credits

**Author:** Derek Merck  
**Organization:** TanglDev  
**Version:** 3.7.2  
**Date:** Winter 2025

Built with: Python 3.13, Pydantic, FastAPI, Vue 3, Vuetify 3, Poetry

Inspired by: Compiler theory, quantum mechanics, Kantian philosophy, STRIPS planning, morphological models, and years of exploring other interactive fiction tools.

---

## FAQ

**Q: Is this production-ready?**  
A: No idea.  It's pretty straightforward to create a reference implementation online, feel free to stress test it and report back.  Core architecture is solid; polish and completeness are in progress.

**Q: Why 37 iterations?**  
A: Your missing keys are always in the last place you look.

**Q: Why not use [existing IF tool]?**  
A: Existing tools are great for their use cases. StoryTangl actually emerged from exploring [Inform][], [Twine][]/Sugarcube, [Ink][], [Ren'Py][], kirikiri, [RPGmaker][], and others. and other interactive fiction platforms.  I adopted or hope to adopt many of the strengths of those systems here.  But StoryTangl comes from a fundamentally different design space: graph-native, planning-first, with best-effort separation between the semantic story space representation and the syntactic presentation layer.

[Inform]: https://ganelson.github.io/inform-website/
[Ink]: https://www.inklestudios.com/ink/
[Twine]: https://twinery.org/
[Ren'Py]: https://www.renpy.org/
[RPGMaker]: https://www.rpgmakerweb.com/

**Q: What's the performance like?**  
A: Optimized for clarity, not speed. It is intended as a reference implementation and platform for theoretical exploration, so I intentionally avoid optimizations that can interfere with simple reasoning about the underlying entities and behaviors. Production systems can borrow the architecture and optimize as needed.

**Q: Can I use this for my game?**  
A: If you understand the architecture and have convinced yourself that it's stable enough, sure. But, be aware that it is designed as a reference, not a turn-key solution.  And although the library API has been fairly stable for a couple of years now, it may evolve as new versions require new endpoints. 

**Q: How do I learn more?**  
A: Read `AGENTS.md` first as it tracks the current state fairly closely.  Then explore `docs/` and study the tests. The codebase itself is heavily documented and meant to be understood by interacting with it.

---

**This is a reference implementation.** It prioritizes correctness, clarity, and architectural integrity over performance or feature count. The goal is to demonstrate a novel approach to interactive narrative that others can learn from and build upon.
