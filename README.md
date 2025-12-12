# StoryTangl

**A Reference Implementation for Graph-based Computational Narratology**

[![CI](https://github.com/derekmerck/storytangl/actions/workflows/ci.yml/badge.svg)](https://github.com/derekmerck/storytangl/actions/workflows/ci.yml) [![docs](https://app.readthedocs.org/projects/storytangl/badge/?version=latest)](https://storytangl.readthedocs.io/en/latest/)

---

## What This Is

StoryTangl is a **research platform** that demonstrates how narrative theory can be implemented and explored using abstract narrative graph and computable systems.

**Core Thesis:** Interactive narratives are best understood as graph structures where player choices collapse possibility spaces into specific story paths—similar to quantum observation collapsing wave functions into measured states.

### What Makes This Different

Most interactive fiction tools (Twine, Ink, Ren'Py) are **authoring environments** optimized for content creation. StoryTangl is a **theoretical validation platform** that:

- **Implements narratological separation of concerns as code** - fabula/episodic process/syuzhet formalism reflected in architectural layering and capabilities
- **Enables formal verification** - Dependency graphs prove narrative coherence (no softlocks, all paths completable)
- **Supports systematic exploration** - Graph topology + semantic embeddings enable directed or exhaustive narrative space navigation
- **Separates structure from presentation** - Same story mechanics can render through different thematic vocabularies

**Use this when:** You want to explore graph-based story generation, or experiment with interactive narrative concepts.

**Use something else when:** You want to ship a game quickly, need mature tooling and community support, or prioritize authoring convenience over architectural purity.

---

## Architecture Overview

### Layered Design

```
core/        → Graph entities, registries, records (domain-agnostic)
ir/          → Intermediate representations (YAML scripts, templates)
journal/     → Narrative fragments and discourse structures  
vm/          → Virtual machine with phase-based execution pipeline
story/       → Domain model (episodes, scenes, actors, locations)
service/     → Orchestrator pattern with controller endpoints
apps/        → CLI, REST API, Vue web client
```

**Dependency flow is strictly unidirectional.** Core never imports from VM; VM never imports from Story; etc. This enables the "compiler metaphor" where higher layers are syntactic sugar over lower-level semantics.

### The Phase Bus (VM Pipeline)

Narrative execution proceeds through eight deterministic phases:

```python
class ResolutionPhase(Enum):
    VALIDATE = 10    # Check preconditions
    PLANNING = 20    # Resolve frontier dependencies
    PREREQS = 30     # Pre-action hooks
    UPDATE = 40      # Apply state changes
    JOURNAL = 50     # Emit narrative fragments
    FINALIZE = 60    # Commit transactions
    POSTREQS = 70    # Post-action hooks
    # (advance cursor)
```

Each phase dispatches registered handlers in priority order, enabling orthogonal concerns (media provisioning, stat checks, logging) to compose without coupling.

**Why this matters:** Narrative manipulations (order, duration, focalization) become **operational** as phase-level transformations.

### Planning & Provisioning

The system implements **proactive dependency resolution**:

1. **Frontier Identification** - VM identifies all reachable-next nodes from cursor
2. **Requirement Discovery** - Each frontier node declares what it needs (actors, items, conditions)
3. **Offer Generation** - Provisioners propose solutions (existing nodes, templates, clones)
4. **Cost-Based Selection** - System picks best offers (prefer existing > modify > create)
5. **Plan Execution** - Selected offers materialize; requirements bind to providers
6. **Viability Assessment** - Unresolved hard requirements mark choices unavailable

### Event Sourcing

Every narrative action records to an append-only ledger:

```python
Ledger = Stream[Record]
Record = (timestamp, phase, handler, payload, outcome)
```

**Benefits:**
- **Deterministic replay** - Rerun any playthrough from seed
- **Formal audit** - Verify planning decisions, trace state evolution
- **Save/load** - Serialize ledger, not graph state
- **Structural analysis** - Mine corpora for dependency patterns

---

## Current Implementation Status

### ✅ Core Systems (Stable)

- **Graph entity model** - Nodes, edges, registries with UUID-based addressing
- **Phase bus execution** - Eight-phase pipeline with handler dispatch
- **Planning & provisioning** - Frontier resolution, offer selection, dependency satisfaction
- **Role/Setting wiring** - YAML scripts create actual dependency edges
- **Event-sourced ledger** - Record stream with multiple persistence backends
- **Service layer** - Orchestrator with controller endpoints, user isolation
- **CLI & REST API** - Functional interfaces for story playback
- **Vue 3 web client** - Working MVP with component testing

### ⚠️ Active Development

- **Media provisioning** - Infrastructure exists; integration with planning incomplete
- **Template scoping** - Registry operational; advanced scope selectors planned
- **Dialog parsing** - Basic speaker attribution; conversational state machines future
- **Reference worlds** - One complete example; expanding demonstration library

### 📋 Research Explorations (Not MVP)

- **Semantic distance metrics** - Quantify narrative similarity, enable interpolation
- **Structural inference** - Extract dependency graphs from play traces (Twine import, etc.)
- **Multi-lane storytelling** - Multiple simultaneous cursors with coordination protocols
- **Continuous interpolation** - Treat narratives as parametric curves, not discrete samples

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/derekmerck/storytangl.git
cd storytangl

# Install with Poetry
poetry install

# Or with pip
pip install -e ".[cli,server]"
```

### Play a Story (CLI)

```bash
# List available worlds
poetry run tangl_info

# Play interactively
poetry run tangl_cli

# Non-interactive playthrough
poetry run tangl_nav reference --auto-select
```

### Start REST API Server

```bash
# Development server
poetry run uvicorn tangl.rest.api_server:app --reload

# Visit http://localhost:8000/docs for interactive API documentation
```

### Run Web Client

```bash
cd apps/web
yarn install
yarn dev

# Visit http://localhost:5173
```

### Python API

```python
from tangl.service.orchestrator import Orchestrator
from tangl.service.controllers import WorldController, RuntimeController

# Initialize
orchestrator = Orchestrator()
orchestrator.register_controller(WorldController())
orchestrator.register_controller(RuntimeController())

user_id = uuid.uuid4()

# Load world
world_info = orchestrator.execute(
    "WorldController.load_world",
    user_id=user_id,
    source="worlds/reference/script.yaml"
)

# Create story session
runtime = orchestrator.execute(
    "WorldController.create_story",
    user_id=user_id,
    world_id=world_info.world_id,
    story_label="session_001"
)

# Get narrative update
update = orchestrator.execute(
    "RuntimeController.get_story_update",
    user_id=user_id,
    ledger_id=runtime.ledger_id
)

# Execute choice
result = orchestrator.execute(
    "RuntimeController.do_action",
    user_id=user_id,
    ledger_id=runtime.ledger_id,
    action_id=update["choices"][0]["uid"]
)
```

---

## Documentation

### For Contributors

Start here to understand the codebase:

1. **`AGENTS.md`** - Coding conventions, architectural principles, testing patterns
2. **`docs/source/contrib/`** - Architecture guides, design patterns, docstring style

### Build Docs Locally

```bash
cd docs
poetry run make html
# Open docs/build/html/index.html
```

---

## Testing

```bash
# Full test suite
poetry run pytest

# Specific layers
poetry run pytest engine/tests/core
poetry run pytest engine/tests/vm
poetry run pytest engine/tests/story

# With coverage
poetry run pytest --cov=tangl --cov-report=html
# Open htmlcov/index.html

# Watch mode (requires pytest-watch)
poetry run ptw
```

**Test philosophy:** Architecture-first, test-after. Use `xfail(strict=True)` for intended-but-unimplemented features. When implementations accidentally pass xfail tests, the test suite errors—forcing you to verify the implementation and remove the marker.

---

## Project Structure

```
storytangl/
├── engine/
│   ├── src/tangl/
│   │   ├── core/          # Graph, entities, registries, records
│   │   ├── ir/            # Intermediate representations (scripts, templates)
│   │   ├── journal/       # Output fragments, discourse structures
│   │   ├── vm/            # Virtual machine, planning, ledger
│   │   ├── story/         # Domain model (episodes, actors, locations)
│   │   ├── service/       # Orchestrator, controllers, user management
│   │   ├── persistence/   # Storage backends (file, Redis, MongoDB, SQLite)
│   │   └── utils/         # Hashing, validation, base models
│   └── tests/             # Comprehensive test suite
├── apps/
│   ├── cli/               # Command-line interface
│   ├── server/            # FastAPI REST API
│   └── web/               # Vue 3 web client
├── docs/                  # Sphinx documentation
├── worlds/                # Reference story bundles
└── scripts/               # Utility scripts
```

---

## Design Philosophy

### 1. Reference Implementation

StoryTangl prioritizes **correctness** and **clarity** over performance. The goal is demonstrating concepts that others can learn from, validate, and build upon. Production systems should borrow the architecture and optimize as needed.

### 2. Theory-First

Architectural decisions map to narratological theory or formal methods:
- Phase bus → narrative operations
- Dependency graphs → Constraint satisfaction  
- Planning → STRIPS-style planning (preconditions + effects)
- Concept and Episode Templates → Proppian morphological functions

### 3. Explicit Over Clever

Prefer small, clear functions over metaprogramming magic. Deterministic behavior beats "flexible" code. Type hints everywhere. No hidden state.

### 4. Compiler Metaphor

Think of StoryTangl as a narrative compiler:
- **YAML scripts** = source language (author-friendly)
- **Graph representation** = intermediate form (runtime-efficient)
- **VM phases** = instruction set architecture
- **Journal fragments** = execution trace
- **Planning system** = linker and optimizer (resolves dependencies ahead of time)

This framing makes the architecture intuitive to software developers.

### 5. Separation of Concerns

Four conceptual layers maintained rigorously:

1. **Story World** (Templates, constraints) - Latent Fabula, what *can* exist
2. **Story Graph** (Scenes, actors, edges) - Realized Fabula, What *does* exist (semantic 'shape')
3. **Story Navigator** (VM, planning) - Episodic process, how we *move through* it
4. **Story Renderer** (Journal, media) - Syuzhet, how we *present* it (syntactic 'appearance')

By keeping these separate, one semantic core can project into many forms—rendered text, audio drama, comic panels, VR experience.

---

## Philosophical Foundations

### Narrative as Quantum Collapse

StoryTangl treats narrative as a **field of potentials**. Story elements exist in superposition—they are possible but not yet real. Player choices cause collapse: specific scenes and events materialize while others remain unrealized.

This isn't just a metaphor. The architecture literally implements:
- **Superposition** → Template nodes can become multiple instances
- **Observation** → Planning phase resolves ambiguity
- **Collapse** → Deterministic materialization through phase bus
- **Entanglement** → Dependency edges link narrative elements

### Kantian Noumena/Phenomena

The story graph is the **noumenal** reality (things-in-themselves); rendered output is **phenomenal** (things-as-perceived). The VM mediates between these realms.

Authors work in the noumenal space (graph structure, dependencies, constraints). Players experience the phenomenal space (text, images, choices). The system ensures **multiple phenomenal presentations** can arise from **single noumenal structure**.

### Platonic Forms

Templates are ideal forms; instances are shadows in the cave. Planning is the mechanism for projecting forms into concrete existence. Vocabulary banks enable the same form to cast different shadows (genre transformations).

---

## Use Cases & Applications

### Academic Research

- **Computational narratology** - Test theories by implementing them
- **Interactive narrative design** - Explore narrative possibility spaces systematically  
- **AI & games** - Narrative planning, procedural generation
- **Digital humanities** - Structural analysis of IF corpora

### Practical Applications

- **IF authoring tool** - Graph-native alternative to Twine with semantic linting (advanced users)
- **Narrative backend** - Drop-in story engine for games
- **Educational platform** - Teaching interactive narrative concepts
- **Experimental narratives** - Multi-lane stories, continuous interpolation, etc.

### What This Is *Not* For

- **Rapid prototyping** - Use Twine, Ink, or Ren'Py for fast iteration
- **Production games** - StoryTangl is reference-grade, not turn-key
- **Non-technical authors** - Leveraging non-trivial features require programming/systems thinking
- **Traditional storytelling** - If you want linear narratives, use a word processor

---

## Performance Considerations

**Current State:**
- Single-threaded per-user session execution
- Memory footprint scales with graph size + journal length
- Planning phase is O(frontier_size × provisioner_count × offers_per_provisioner)
- No caching or memoization yet (deferred for clarity)

**Optimizations Available:**
- Pre-plan stories at compile time (eager mode)
- Cache provisioning results
- Incremental graph serialization
- Graph database backends (Neo4j, etc.)

**Design Trade-off:** We deliberately avoid optimizations that would obscure the conceptual model. Reference implementations should be **easy to understand**, not fast. Production systems can profile and optimize hotspots.

---

## Contributing

### Before Starting

1. Read `AGENTS.md` for conventions
2. Explore `docs/source/contrib/` for patterns
3. Study tests—they document intended behavior
4. Run the test suite successfully

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/my-exploration

# Make changes, write tests
poetry run pytest

# Type checking
poetry run mypy engine/src/tangl

# Lint (if configured)
poetry run flake8 engine/src

# Commit and push
git commit -am "Add exploration of X"
git push origin feature/my-exploration
```

### What We Value

- **Theoretical grounding** - Patterns based on formal systems
- **Architectural integrity** - Respect layer boundaries
- **Test coverage** - Write tests that validate concepts
- **Documentation** - Explain *why*, not just *what*
- **Clarity** - Simple code beats clever code

---

## Roadmap

### Short-term (Current Focus)

- Complete media provisioning integration
- Expand reference world library
- Write theory validation papers (no new code required)
- Clean up stale design documentation

### Medium-term (Next 6-12 Months)

- Semantic distance metrics (shape space exploration)
- Proppian pattern library (re-entrant subgraphs)
- Vocabulary substitution framework (parametric thematics)

### Long-term (Research Directions)

- Structural inference from play traces
- Multi-lane storytelling with coordination
- Continuous narrative interpolation
- Learning-based provisioning

---

## FAQ

**Q: Is this production-ready?**  
A: The core architecture is solid and battle-tested through comprehensive test suite. Individual subsystems vary in completeness. Use at your own risk; this is a reference implementation, not a turn-key solution.

**Q: Why 37 iterations before v3.7?**  
A: Your missing keys are always in the last place you look.

**Q: Why not use [existing IF tool]?**  
A: Twine, Ink, Inform, and Ren'Py are excellent for their purposes. StoryTangl comes from a fundamentally different design space: **graph-native, theory-first, formally verifiable**. Use those tools to ship games; use StoryTangl to explore what's computationally possible in narrative.

**Q: What's the performance like?**  
A: Optimized for **correctness** and **clarity**, not speed. Fast enough for academic research and prototyping; could be optimized for use with production applications. The architecture supports scaling, but this implementation prioritizes understanding over throughput.

**Q: Can I use this for my game/app/research?**  
A: If you understand the architecture and accept that it's research-grade, sure. Be aware that APIs may evolve as new insights require new abstractions. This is not a stable 1.0 product—it's an ongoing research platform.

**Q: How do I learn more?**  
A: Read `AGENTS.md` → Study tests → Explore `docs/source` → Build a world and extend it with interesting mechanics. The codebase is meant to be understood through interaction, not passive reading.

---

## License

MIT License - See `LICENSE` file for details.

Exception: Demographics module name-banks use BSD-licensed content from external sources. See `engine/src/tangl/mechanics/demographics/` for attribution.

---

## Credits

**Author:** Derek Merck  
**Organization:** TanglDev  
**Version:** 3.7.2  
**Date:** Winter 2025

**Built with:** Python 3.13, Pydantic, FastAPI, Vue 3, Vuetify 3, Poetry

**Inspired by:** Compiler theory, quantum mechanics, Kantian philosophy, STRIPS planning, morphological analysis, and decades of interactive fiction tools (Inform, Twine, Ink, Ren'Py, RPG Maker).

**Special thanks to:** The narratology community for 50+ years of theory that can now be tested computationally.

---

**This is a reference implementation.** It prioritizes correctness, clarity, and theoretical integrity over features or performance. The goal is demonstrating novel approaches to interactive narrative that others can learn from, validate, and build upon.

**Read. Understand. Extend. Publish.**
