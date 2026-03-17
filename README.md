# StoryTangl

**A research platform for graph-based computational narratology.**

[![CI](https://github.com/derekmerck/storytangl/actions/workflows/ci.yml/badge.svg)](https://github.com/derekmerck/storytangl/actions/workflows/ci.yml)
[![docs](https://app.readthedocs.org/projects/storytangl/badge/?version=latest)](https://storytangl.readthedocs.io/en/latest/)

StoryTangl models interactive narrative as a graph of interdependent
possibilities that collapses into a specific story through traversal.
Authors define a *possibility space* — characters, events, places, and the
rules connecting them.  Readers navigate that space, and the engine
resolves dependencies, tracks state, and emits a linear narrative journal.

The name started as a backronym for *the Abstract Narrative Graph Library*.
It stuck because the engine's real job is **untangling** — extracting a
coherent story thread from a combinatorial web of requirements and
consequences.

---

## Why StoryTangl

Most interactive fiction tools are **authoring environments** optimized for
content creation.  StoryTangl is a **theoretical validation platform**.

**It implements narrative theory as executable code.**  The architecture
maps directly to established narratological concepts: Bal's fabula/story/text
trinity becomes graph/navigation/journal; Chatman's kernels and satellites
become required and optional dependency edges; Genette's discourse operations
become phase-bus transformations.  If the theory is right, the code works.
If the code breaks, the theory has a gap worth studying.

**It enables formal verification.**  Dependency graphs can prove structural
properties — no softlocks, all paths completable, every role satisfiable —
before a single word of prose is rendered.

**It separates structure from presentation.**  The same story mechanics
render through different thematic vocabularies, different media pipelines,
and different client interfaces without changing the underlying graph.

### When to use it

Use StoryTangl when you want to explore computational narratology,
experiment with graph-based story structures, build interactive narrative
research tools, or need a formally-specified narrative engine with
deterministic replay.

Use something else when you want to ship a game quickly, need mature
tooling and a large community, or want a WYSIWYG authoring experience.

---

## How It Works

### The Three-Layer Model

```
Fabula          The possibility space — all events, characters, and
(graph)         relationships that could be narrated.

                         ↓  traverse + resolve

Episodic        The resolution process — cursor-driven traversal that
Process         provisions dependencies, applies effects, and emits
(VM)            content at each step.

                         ↓  emit fragments

Syuzhet         The realized narrative — a linear journal of prose,
(journal)       choices, and media as experienced by the reader.
```

An author writes **scripts** (YAML) that a **compiler** transforms into a
story graph.  A **materializer** instantiates the graph for a specific
playthrough.  As the reader makes choices, the **VM** walks the graph
through an eight-phase pipeline:

    VALIDATE → PLANNING → PREREQS → UPDATE → JOURNAL → FINALIZE → POSTREQS → advance

Each phase is a dispatch point where registered handlers run in priority
order and return auditable receipts.  The system is **event-sourced** — every
state change is a ledger entry, so any playthrough is reproducible from a
snapshot plus the choice log.

### Provisioning

Before a node is visited, the engine **proactively resolves its
dependencies**.  If a scene requires "a villain," the resolver searches for
matching actors by proximity and specificity, proposes offers, and binds
the best candidate.  This is the mechanism that collapses possibility into
commitment — once bound, a role assignment is frozen for the rest of the
story.

### Extensibility

Story mechanics (minigames, dialog systems, world-specific rules) plug in
as **behaviors** registered at specific pipeline phases with scoped
priority.  A five-layer dispatch cascade (SYSTEM → APPLICATION → DOMAIN →
INSTANCE → INLINE) lets world authors override engine defaults without
modifying core code.

For a deeper treatment of the conceptual foundations, see
[`docs/src/design/story/philosophy.md`](docs/src/design/story/philosophy.md).

---

## Project Structure

```
storytangl/
├── engine/
│   ├── src/tangl/              # Core engine package
│   │   ├── core/               # Timeless primitives: entity, graph, dispatch
│   │   ├── vm/                 # Temporal evolution: frame, phases, provisioning
│   │   ├── story/              # Narrative semantics: episodes, concepts, journal
│   │   ├── prose/              # Text-facing parsing and voice helpers
│   │   ├── media/              # Asset generation, inventory, and delivery
│   │   ├── service/            # Lifecycle: gateway, orchestrator, controllers
│   │   ├── persistence/        # Storage abstraction across backends
│   └── tests/                  # Test suite mirroring src/ structure
├── apps/
│   ├── cli/                    # cmd2-based command-line interface
│   ├── server/                 # FastAPI REST API
│   └── web/                    # Vue 3 + TypeScript web client
├── docs/                       # Sphinx docs, published design notes, API reference
├── worlds/                     # Reference story bundles
└── scripts/                    # Utility and analysis scripts
```

Key engine subpackages carry code-adjacent `*_DESIGN.md` notes with
architectural intent, design decisions, and contracts. These are the
authoritative package-level references for how each layer works:

| Layer | Design Docs | Scope |
|-------|-------------|-------|
| **core** | [`CORE_DESIGN.md`](engine/src/tangl/core/CORE_DESIGN.md) | Entity, graph, dispatch, templates, serialization |
| **vm** | [`VM_DESIGN.md`](engine/src/tangl/vm/VM_DESIGN.md) | Phases, provisioning, namespace, traversal, replay |
| **story** | [`STORY_DESIGN.md`](engine/src/tangl/story/STORY_DESIGN.md) | Fabula compilation, journal, concepts, choices |
| **service** | [`SERVICE_DESIGN.md`](engine/src/tangl/service/SERVICE_DESIGN.md) | Gateway, orchestrator, response envelopes |
| **media** | [`MEDIA_DESIGN.md`](engine/src/tangl/media/MEDIA_DESIGN.md) | Inventory, media deps, creator pipeline, service dereference boundary |

---

## Getting Started

### Prerequisites

- Python ≥ 3.12
- [Poetry](https://python-poetry.org/) for dependency management
- Node.js 18+ and Yarn (for the web client)

### Install

```bash
git clone https://github.com/derekmerck/storytangl.git
cd storytangl
poetry install              # engine + dev dependencies
```

Optional extras:

```bash
poetry install -E server    # FastAPI + uvicorn + cmd2
poetry install -E cli       # cmd2 CLI only
```

### Run the Tests

```bash
# Full engine suite
poetry run pytest

# Individual layers
poetry run pytest engine/tests/core
poetry run pytest engine/tests/vm
poetry run pytest engine/tests/story

# With coverage
poetry run pytest --cov=tangl --cov-report=html

# Web client
cd apps/web && yarn install && yarn test
```

### Play a Story

```bash
# CLI — interactive mode
poetry run tangl-cli

# REST server
poetry run tangl-serve
# then open http://localhost:8000/docs for the OpenAPI explorer

# Web client (requires server running)
cd apps/web && yarn dev
# then open http://localhost:5173
```

---

## Documentation

### For Users and Authors

Full documentation builds with Sphinx and hosts on Read the Docs:

```bash
cd docs
poetry run make html
open build/html/index.html
```

### For Contributors

Start here, in this order:

1. **`AGENTS.md`** — Coding conventions, layer boundaries, testing
   patterns, core abstractions
2. **`docs/src/contrib/`** — Coding style guide, docstring conventions,
   exception policy
3. **`*_DESIGN.md`** files in each subpackage — Architectural intent and
   contracts for the layer you're working in

### For Researchers

- **[`docs/src/design/story/philosophy.md`](docs/src/design/story/philosophy.md)** — Conceptual foundations:
  fabula/syuzhet separation, narrative debt, parametric story space
- **[`docs/src/design/glossary.md`](docs/src/design/glossary.md)** — Canonical vocabulary mapping
  narratological concepts to implementation
- **`storytangl-research-agenda.md`** — Open problems and exploration
  directions
- **`StoryTangl_Lit_Review_2025.pdf`** — Annotated bibliography of
  classical and interactive narratology

---

## Contributing

Contributions are welcome.  Please read `AGENTS.md` before starting — it
covers the conventions that matter most:

- **Type hints everywhere.**  Functions, methods, attributes, return types.
- **Respect layer boundaries.**  `core → vm → story → service` — lower
  layers never import from higher ones.
- **Small, explicit functions** over metaprogramming or implicit behavior.
- **RST docstrings** for Sphinx compatibility, following the conventions in
  `docs/src/contrib/docstring_style.md`.
- **Tests validate behavior**, not implementation.  Use `xfail(strict=True)`
  for intended-but-unimplemented features.

### Workflow

1. Read `AGENTS.md` and the relevant `*_DESIGN.md`
2. Create a feature branch
3. Write or update tests
4. Implement
5. Verify: `poetry run pytest` passes, types check clean
6. Open a PR with a clear description of *what* and *why*

---

## Research Directions

StoryTangl is positioned as a research platform for computational
narratology.  Active and planned explorations include:

- **Narrative planning as linear logic** — mapping dependency resolution to
  Martens' Ceptre formalism for formal proof of narrative coherence
- **Narrative shape space** — semantic distance metrics for quantifying
  story similarity and enabling continuous interpolation
- **Proppian re-entrant patterns** — compressing interactive narratives
  through morphological function templates
- **Parametric discourse** — projecting the same fabula through different
  thematic vocabularies ("tell this story as noir / comedy / horror")
- **Multi-lane storytelling** — multiple navigators traversing shared
  fabula simultaneously with coordination protocols
- **Structural inference** — recovering approximate story graphs from
  existing IF corpora (Twine, Ink, ChoiceScript)

See `storytangl-research-agenda.md` for detailed problem statements and
proposed approaches.

---

## Acknowledgments

StoryTangl has been in development since 2021 across roughly 38
architectural iterations — from a gamebook parser to a full narrative
virtual machine.  It draws on the author's background in medical imaging
(shape theory, signal processing, high-dimensional optimization) and
literary theory (undergraduate thesis on Sterne's *Tristram Shandy*,
complete with hand-drawn MacPaint plot diagrams).

The theoretical foundations rest on work by Mieke Bal, Gérard Genette,
Seymour Chatman, Roland Barthes, Vladimir Propp, Espen Aarseth,
Marie-Laure Ryan, Emily Short, Chris Martens, and others whose ideas
about narrative structure turned out to be eminently computable.

Development has been significantly aided by AI coding agents, who serve
as tireless architectural reviewers and occasionally suggest things that
are actually good.

---

## Version History

| Epoch | Year | Focus |
|-------|------|-------|
| 3.7–3.8 | 2025–2026 | Dependency-driven VM, layered dispatch, AI agent collaboration |
| 3.2 | 2025 | Three-layer narrative graph, provisioning architecture |
| 2.9 | 2024 | Strategy-based task handlers |
| 2.8 | 2023 | Pydantic migration, structured serialization |
| 2.5 | 2022 | Vue 3 web client, SVG avatar system |
| 2.3 | 2021 | Modular worlds, initial Vue 2 client |

For detailed change history, see `CHANGELOG.md`.

---

## License

MIT — see `LICENSE` for details.
