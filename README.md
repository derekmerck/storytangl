# StoryTangl

**A Research Platform for Graph-Based Computational Narratology**

[![CI](https://github.com/derekmerck/storytangl/actions/workflows/ci.yml/badge.svg)](https://github.com/derekmerck/storytangl/actions/workflows/ci.yml) [![docs](https://app.readthedocs.org/projects/storytangl/badge/?version=latest)](https://storytangl.readthedocs.io/en/latest/)

---

## What This Is

StoryTangl is a **research platform** that implements narrative theory as executable code. It's designed for exploring how linear and interactive narrative spaces can be formally modeled, verified, and dynamically manipulated.

**Core thesis:** Interactive narratives can be represented as graph structures where reader choices collapse possibility spaces into specific story paths. By modeling narrative as a computable embedding in a story-space, we can validate narratological theory, prove structural coherence, and enable systematic exploration of narrative space.

### What Makes This Different

Most interactive fiction tools (Twine, Ink, Ren'Py) are **authoring environments** optimized for content creation. StoryTangl is a **theoretical validation platform** that:

- **Implements narratological theory as code** — semantics (fabula), structure (episodic process), and syntax (syuzhet) modeled as constellations of data structures, operations, and behaviors
- **Enables formal verification** — Dependency graphs prove narrative coherence (no softlocks, all paths completable)
- **Supports systematic exploration** — Graph topology + semantic analysis enable exhaustive narrative space navigation
- **Separates structure from presentation** — Same story mechanics can render through different thematic vocabularies

### When to Use StoryTangl

**Use this when:** You want to explore computational narratology, experiment with graph-based story structures, build interactive narrative research tools, or need a formally-specified narrative engine.

**Use something else when:** You want to ship a game quickly, need mature tooling and community support, or prioritize authoring convenience over architectural clarity.

---

## Current Status (v3.7)

StoryTangl is at **MVP milestone** — core systems are stable and functional, with active development on polish and demonstration content.

### ✅ Working Systems

| System | Status | Notes |
|--------|--------|-------|
| **Graph entity model** | Stable | Nodes, edges, registries with UUID addressing |
| **Phase bus execution** | Stable | Eight-phase pipeline with handler dispatch |
| **Planning & provisioning** | Stable | Frontier resolution, offer selection, dependency satisfaction |
| **Event-sourced ledger** | Stable | Record stream with multiple persistence backends |
| **Service layer** | Stable | Orchestrator with controller endpoints, user isolation |
| **CLI** | Functional | Interactive story playback |
| **REST API** | Functional | FastAPI server with OpenAPI docs |
| **Web client** | MVP Complete | Vue 3 + TypeScript, component testing |

### ⚠️ Active Development

- **Media provisioning** — Infrastructure exists; full integration with planning phase incomplete
- **Reference worlds** — One complete example; expanding demonstration library
- **Template scoping** — Registry operational; advanced scope selectors planned

### 📋 Research Explorations (Not MVP)

- Semantic distance metrics for narrative similarity
- Structural inference from play traces (Twine import)
- Multi-lane storytelling with coordination protocols
- Continuous narrative interpolation

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/derekmerck/storytangl.git
cd storytangl

# Install with Poetry (recommended)
poetry install

# Or with pip
pip install -e ".[cli,server]"
```

### Play a Story (CLI)

```bash
# System info
poetry run tangl-info

# Interactive play
poetry run tangl-cli
```

### Start REST API Server

```bash
# Development server
poetry run tangl-serve

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
import uuid

# Initialize orchestrator
orchestrator = Orchestrator()
orchestrator.register_controller(WorldController())
orchestrator.register_controller(RuntimeController())

user_id = uuid.uuid4()

# Load a world
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

# Get current narrative state
update = orchestrator.execute(
    "RuntimeController.get_story_update",
    user_id=user_id,
    ledger_id=runtime.ledger_id
)

# Execute a choice
result = orchestrator.execute(
    "RuntimeController.do_action",
    user_id=user_id,
    ledger_id=runtime.ledger_id,
    action_id=update["choices"][0]["uid"]
)
```

---

## Architecture Overview

### Layered Design

```
engine/src/tangl/
├── core/        → Graph entities, registries, records (domain-agnostic)
├── vm/          → Virtual machine with phase-based execution pipeline
├── story/       → Domain model (episodes, scenes, actors, locations)
├── ir/          → Intermediate fabula representations (YAML scripts, templates)
├── journal/     → Narrative fragments and discourse structures
└── service/     → Orchestrator pattern with controller endpoints

apps/
├── cli/         → Command-line interface
├── server/      → FastAPI REST API
└── web/         → Vue 3 web client
```

**Dependency flow is strictly unidirectional.** Core never imports from VM; VM never imports from Story. This enables the "compiler metaphor" where higher layers are syntactic sugar over lower-level semantics.

### Planning & Provisioning

The system implements **proactive dependency resolution**:

1. **Frontier identification** — VM identifies reachable-next nodes from cursor
2. **Requirement discovery** — Each frontier node declares what it needs
3. **Offer generation** — Provisioners propose solutions (existing nodes, templates, clones)
4. **Cost-based selection** — System picks best offers (prefer existing > modify > create)
5. **Plan execution** — Selected offers materialize; requirements bind to providers
6. **Viability assessment** — Unresolved hard requirements mark choices unavailable

### Event Sourcing

Every narrative action records to an append-only ledger:

```python
Ledger = Stream[Record]
Record = (timestamp, phase, handler, payload, outcome)
```

This enables deterministic replay, formal audit trails, and structural analysis of playthroughs.

---

## Project Structure

```
storytangl/
├── engine/
│   ├── src/tangl/         # Core engine package
│   └── tests/             # Comprehensive test suite
├── apps/
│   ├── cli/               # Command-line interface
│   ├── server/            # FastAPI REST API
│   └── web/               # Vue 3 web client
├── docs/                  # Sphinx documentation
├── worlds/                # Reference story bundles
│   └── reference/         # "The Crossroads Inn" demo world
├── deployment/            # Docker configuration
└── scripts/               # Utility scripts
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

# Web client tests
cd apps/web && yarn test
```

**Test philosophy:** Architecture-first, test-after. Use `xfail(strict=True)` for intended-but-unimplemented features.

---

## Documentation

### For Contributors

Start here to understand the codebase:

1. **`AGENTS.md`** — Coding conventions, architectural principles, testing patterns
2. **`docs/source/contrib/`** — Architecture guides, design patterns, docstring style

### Build Docs Locally

```bash
cd docs
poetry run make html
# Open docs/build/html/index.html
```

---

## Research Directions

StoryTangl is positioned as a research platform. Current explorations include:

**Theoretical validation:**
- Proving equivalence between dependency systems and linear logic
- Testing whether narratological taxonomies are computationally complete
- Documenting where theory underdetermines implementation

**Novel contributions:**
- Semantic distance metrics for quantifying narrative similarity
- Continuous interpolation through narrative space
- Multi-lane storytelling with coordination protocols
- Structural inference from existing IF corpora

---

## Version History

| Version | Year | Focus |
|---------|------|-------|
| 3.7 | 2025 | Dependency-driven interpreter, AI code agents |
| 3.2 | 2025 | Three-layer narrative graph |
| 2.9 | 2024 | Strategy-based task handlers |
| 2.8 | 2023 | Switch attrs→pydantic, better serialization |
| 2.5 | 2022 | Vue 3/Vite client, SVG avatars |
| 2.3 | 2021 | Modular worlds, Vue 2 client |

---

## Contributing

We welcome contributions! Please read `AGENTS.md` for coding conventions and architectural guidance before submitting PRs.

Key principles:
- Type hints everywhere
- Respect layer boundaries (core → vm → story → service)
- Small, explicit functions over metaprogramming magic
- RST docstrings for Sphinx compatibility

---

## License

MIT — See LICENSE file for details.
