# StoryTangl v3.7

**TanglDev, Fall 2025**  

[![CI](https://github.com/derekmerck/storytangl/actions/workflows/ci.yml/badge.svg)](https://github.com/derekmerck/storytangl/actions/workflows/ci.yml)

**A graph-based narrative engine for interactive storytelling**

---

[//]: # (<picture>)

[//]: # (  <source media="&#40;prefers-color-scheme: dark&#41;" srcset="brand/storytangl_logo-im-dark.png">)

[//]: # (  <source media="&#40;prefers-color-scheme: light&#41;" srcset="brand/storytangl_logo-im.png">)

[//]: # (  <img alt="Fallback image description" src="brand/storytangl_logo-im.png" width="100%" height="50px">)

[//]: # (</picture>)

## What This Is

StoryTangl is a **reference implementation** of a sophisticated graph-based narrative system. It demonstrates a novel architecture where stories exist as abstract graphs that "collapse" into linear narratives through player choices—think quantum superposition for interactive fiction.

This is version 3.7, representing the ~37th architectural iteration (4 rewrites with 8-12 iterations each). The current focus is reaching **MVP status** with clean, working fundamentals rather than shipping aspirational features.

### Project Status

**What Works Now:**
- ✅ Three-layer architecture (Core/VM/Story) with clean separation
- ✅ Event-sourced execution with ledger persistence
- ✅ Eight-phase VM pipeline with deterministic resolution
- ✅ Planning & provisioning system for dynamic narrative construction
- ✅ YAML-based story scripting with validation
- ✅ Linear narrative playback (CLI and REST API)
- ✅ Multiple persistence backends (memory, file, Redis, MongoDB)
- ✅ Vue 3.5 web client (functional MVP)
- ✅ Comprehensive test coverage with pytest

**In Progress:**
- ⚙️ Final integration of story dispatch into VM pipeline
- ⚙️ Role/setting provisioning from story scripts
- ⚙️ Media provisioning infrastructure completion
- ⚙️ Web client modernization to Vue 3.5 + TypeScript

**Post-MVP:**
- 📋 Branching narratives with state tracking
- 📋 Conditional content and guard clauses
- 📋 Dynamic media generation
- 📋 Sandbox mechanics (maps, schedules, etc.)

---

## Architecture Highlights

StoryTangl's distinguishing features come from its architectural choices:

### Clean Layering
```
core   → Generic graph entities, registries, records
vm     → Narrative virtual machine with phase-based execution
story  → Domain model (episodes, scenes, actors, locations)
service → Orchestrator pattern with controller endpoints
apps   → CLI, REST API, web client
```

**Dependency flow is strictly one-way.** Lower layers never import from higher ones.

### Phase Bus Execution

The VM uses an eight-phase execution cycle for deterministic, auditable narrative resolution:

1. **VALIDATE** - Check preconditions
2. **PLANNING** - Resolve frontier dependencies (provision needed resources)
3. **PREREQS** - Pre-transition hooks
4. **UPDATE** - Apply state changes
5. **JOURNAL** - Generate narrative output
6. **FINALIZE** - Commit planning decisions
7. **POSTREQS** - Post-transition hooks
8. **Advance** - Move cursor

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

# For CLI instead, override entrypoint
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
- Design docs near relevant code (e.g., `engine/src/tangl/vm/provision/notes-planning_design.md`)

### Project Structure

```
storytangl/
├── engine/
│   ├── src/tangl/
│   │   ├── core/          # Graph entities, registries, records
│   │   ├── vm/            # Virtual machine, planning, ledger
│   │   ├── story/         # Domain model (episodes, actors, etc.)
│   │   ├── service/       # Orchestrator, controllers
│   │   └── persistence/   # Storage backends
│   └── tests/             # Comprehensive test suite
├── apps/
│   ├── cli/               # Command-line interface
│   ├── server/            # FastAPI REST API
│   └── web/               # Vue 3.5 web client
├── docs/                  # Sphinx documentation
└── worlds/                # Example story content
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

### Python API

For direct integration:

```python
from tangl.service.orchestrator import Orchestrator
from tangl.service.controllers import RuntimeController, WorldController

# Initialize orchestrator
orchestrator = Orchestrator()

# Load a world
world_id = orchestrator.execute(
    "WorldController.load_world",
    user_id="user123",
    source="path/to/story.yaml"
)

# Create story session
story_id = orchestrator.execute(
    "RuntimeController.create_story",
    user_id="user123",
    world_id=world_id,
    story_label="session_001"
)

# Get current state
update = orchestrator.execute(
    "RuntimeController.get_story_update",
    user_id="user123"
)

# Make choice
result = orchestrator.execute(
    "RuntimeController.do_action",
    user_id="user123",
    action_id=update["choices"][0]["uid"]
)
```

The orchestrator handles all resource hydration and persistence automatically.

---

## Performance & Scale

**Current State:**
- Optimized for **correctness** over speed (reference implementation)
- Single-threaded execution within a user session
- Concurrent users isolated via per-user locking
- Memory footprint scales with graph size + journal length

**Typical Performance:**
- Story initialization: ~100-500ms
- Choice resolution: ~50-200ms (including planning)
- Journal retrieval: ~10-50ms

**Persistence:**
- In-memory: Instant, ephemeral
- File-based: ~50-100ms per save
- Redis: ~10-20ms per operation
- MongoDB: ~20-50ms per operation

For production use, Redis is recommended for session state with MongoDB for long-term storage.

**Scaling Strategy:**
- Horizontal: Each user session is independent
- Stateless API servers can scale freely
- Shared persistence layer (Redis cluster)
- CDN for media assets

---

## Philosophical Foundations

### Why This Architecture?

StoryTangl's design draws from multiple intellectual traditions:

**Kantian Framework:** The story graph is the "noumenal" reality (things-in-themselves), while rendered output is "phenomenal" (things-as-perceived). The VM mediates between these realms.

**Platonic Forms:** Templates are ideal forms; instances are shadows in the cave. The planning system is the mechanism for projecting forms into concrete existence.

**Compiler Theory:** YAML→Graph→Journal is a compilation pipeline with intermediate representations at each stage. The phase bus is an instruction set architecture for narrative execution.

**AI Planning (STRIPS):** Requirements specify preconditions; provisioners apply operators; the planning cycle searches the state space of possible narratives.

**Morphological Models:** The story world is a shape model defining the space of valid narratives. Story instances are specific shapes sampled from this space.

These aren't mere analogies—they're design principles that shaped concrete technical choices.

### Evolution Through Iteration

This is version 3.7, representing roughly 37 architectural rewrites over several years. The key learnings:

1. **Three-layer separation** emerged after multiple failed attempts at monolithic systems
2. **Phase bus** replaced brittle event handlers and task chains
3. **Event sourcing** solved replay and debugging problems
4. **Type purity** eliminated subtle serialization bugs
5. **Planning-first** prevents softlocks better than backtracking
6. **Template-driven** scales better than hardcoded content

Each major version abandoned working code to get the architecture right. The current design is stable because it's been battle-tested through repeated rebuilds.

---

## Roadmap

### MVP Completion (Current Focus)

- [ ] Finish story dispatch integration into VM pipeline
- [ ] Complete role/setting provisioning from scripts
- [ ] Wire media provisioning infrastructure
- [ ] Comprehensive reference stories
- [ ] Documentation polish
- [ ] Public release (transition from private development)

### Phase 2 (Post-MVP)

- [ ] Branching narratives with choice trees
- [ ] Conditional content (guards, facts, predicates)
- [ ] Save/load system for player sessions
- [ ] Media forge integration (image generation, etc.)
- [ ] Narrator subsystem (dynamic text generation)
- [ ] Web client modernization (Vue 3.5 + TypeScript strict)

### Phase 3 (Future Research)

- [ ] Sandbox mechanics (maps, schedules, mobile actors)
- [ ] Specialized asset types (inventory, wearables, etc.)
- [ ] Continuous narrative interpolation
- [ ] Constraint satisfaction with SAT solver
- [ ] Multiplayer story sessions
- [ ] Advanced AI integration (LLM-assisted authoring/generation)

---

## Contributing

StoryTangl is currently in **private development** until MVP is reached. The repository will become public once the reference implementation demonstrates working functionality that matches documentation claims.

If you're a collaborator:

1. **Read `AGENTS.md` first** - Contains all coding conventions
2. **Study the layer boundaries** - Respect the architecture
3. **Write tests** - Use xfail for intended features
4. **Document thoroughly** - This is a reference implementation
5. **Ask questions** - Better to clarify than assume

### Key Conventions

- Python 3.13+ with full type hints
- Pydantic for all data models
- pytest with comprehensive coverage
- Black-like formatting (4-space indent)
- Sphinx for documentation (reStructuredText)
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

Inspired by: Compiler theory, quantum mechanics, Kantian philosophy, STRIPS planning, morphological models, and years of frustration with traditional interactive fiction tools.

---

## FAQ

**Q: Is this production-ready?**  
A: Not yet. It's approaching MVP but still in active development. Core architecture is solid; polish and completeness are in progress.

**Q: Why 37 iterations?**  
A: Getting the architecture right required multiple strategic rewrites. We prioritized correctness over shipping quickly.

**Q: Why not use [existing IF tool]?**  
A: Existing tools are great for their use cases. StoryTangl explores a different design space: graph-native, planning-first, with clean separation between story logic and presentation.

**Q: What's the performance like?**  
A: Optimized for clarity, not speed. It's a reference implementation. Production systems can borrow the architecture and optimize as needed.

**Q: Can I use this for my game?**  
A: Once it's public and you understand the architecture, yes. Be aware it's designed as a reference, not a turn-key solution.

**Q: How do I learn more?**  
A: Read `AGENTS.md`, explore `docs/`, study the tests. The codebase is meant to be understood by reading it.

---

**This is a reference implementation.** It prioritizes correctness, clarity, and architectural integrity over raw performance or feature count. The goal is to demonstrate a novel approach to interactive narrative that others can learn from and build upon.
