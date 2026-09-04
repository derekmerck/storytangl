<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)"
            srcset=".github/assets/README-banner-dark.png">
    <img src=".github/assets/README-banner.png"
         alt="StoryTangl - a research platform for graph-based computational narratology"
         width="860">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/derekmerck/storytangl/actions/workflows/ci.yml"><img
     src="https://github.com/derekmerck/storytangl/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://storytangl.readthedocs.io/en/latest/"><img
     src="https://app.readthedocs.org/projects/storytangl/badge/?version=latest" alt="docs"></a>
</p>

# StoryTan⅁l

StoryTangl models interactive narrative as a graph of interdependent
possibilities that collapses into a specific story through traversal. Authors
define a possibility space: characters, events, places, assets, rules,
requirements, and relationships. Readers or other navigators move through that
space, and the engine resolves dependencies, tracks state, and emits a linear
narrative journal.

The name started as a backronym for *the Abstract Narrative Graph Library*. It
stuck because the engine's real job is **untangling**: extracting a coherent
story thread from a combinatorial web of requirements and consequences.

---

## See It Run

```bash
git clone https://github.com/derekmerck/storytangl.git
cd storytangl
poetry install
poetry run tangl-cli
```

Inside the shell, `create_user <secret>` registers a local player. Then pick a
world and start making choices:

<p align="center">
  <img src=".github/assets/cli-session.png"
       alt="A StoryTangl CLI session: starting the coronate_the_regent world, provoking a dragon, and being offered a dragonslayer sword"
       width="620">
</p>

That warning to the dragon is not flavour text. It grants the player an
`irritated_dragon` condition, and a later scene tests for it and compels a
confrontation the story otherwise skips -- while the merchant's sword, offered
one beat earlier, is the hedge against exactly that. The choice and its payoff
are never wired directly to each other; the consequence travels as state.

### The same story, wearing something else

A different world, `repartee_loop`, at the same opening beat -- rendered twice
through the pygame port:

<p align="center">
  <img src=".github/assets/repartee-quay.png"
       alt="The repartee_loop opening beat in the quayside art pack: a clerk reading papers on a harbour dock at golden hour"
       width="49%">
  <img src=".github/assets/repartee-spaceport.png"
       alt="The same beat in the spaceport art pack: a service robot on a night dock under a moon"
       width="49%">
</p>

The prose is identical. The choice is identical. The graph, the script, the
staging hints and the client are all untouched. One line of `world.yaml`
selects the pack:

```yaml
media_dir: media_spaceport   # default: media
```

Structure and presentation are separate objects here, so a reskin is a
different *reading* of one story rather than a second story.

### Many stories, many skins, many realizations

Eighteen reference worlds ship in [`worlds/`](worlds/), from a blackjack
parlour to a hall-monitor credential check. Each renders through whichever
surface is asked for -- a text floor, a pixel-art stage, a REST service, a web
client, a Ren'Py export -- from the same fragment stream, and each accepts
whatever art pack it is pointed at. See
[Run The Reference Apps](#run-the-reference-apps), and
[`worlds/repartee_loop/`](worlds/repartee_loop/) for how a pack is built and
captured.

---

## Why StoryTangl

Most interactive fiction tools are authoring environments optimized for content
creation. StoryTangl is a theoretical validation platform and reference
implementation for narrative systems.

**It implements narrative theory as executable code.** The architecture maps to
established narratological concepts: Bal's fabula/story/text trinity becomes
graph/navigation/journal; Chatman's kernels and satellites become required and
optional dependency edges; Genette's discourse operations become phase-bus
transformations.

**It makes structural analysis and validation possible.** The current
preflight and diagnostic surfaces report loader, compiler, and runtime findings.
Broader reachability, finishability, and solver-backed analysis remain active
research rather than a finished authoring product.

**It is a constraint-driven narrative engine.** Partial specifications such as
"a scene needs a villain" can be resolved at runtime through provisioning,
collapsing abstract requirements into concrete bindings.

**It separates structure from presentation.** The same mechanics can render
through different thematic vocabularies, media pipelines, client interfaces,
and presentation profiles without changing the underlying graph.

### When To Use It

Use StoryTangl when you want to explore computational narratology, experiment
with graph-based story structures, build interactive narrative research tools,
or work with a formally specified narrative engine with deterministic replay.

Use something else when you want to ship a game quickly, need mature authoring
tooling and a large community, or want a WYSIWYG writing environment.

---

## How It Works

### The Three-Layer Model

```text
Fabula          The possibility space: all events, characters, and
(graph)         relationships that could be narrated.

                         ↓ traverse + resolve

Episodic        The resolution process: cursor-driven traversal that
Process         provisions dependencies, applies effects, and emits
(VM)            content at each step.

                         ↓ emit fragments

Syuzhet         The realized narrative: a linear journal of prose,
(journal)       choices, and media as experienced by the reader.
```

An author writes scripts, commonly YAML or another loader-supported format.
The compiler normalizes those scripts into StoryTangl's story graph. A
materializer instantiates that graph for a specific playthrough.

As the reader makes choices, the VM walks the graph through an ordered phase
pipeline:

```text
VALIDATE -> PLANNING -> PREREQS -> UPDATE -> JOURNAL -> FINALIZE -> POSTREQS -> advance
```

Each phase is a dispatch point where registered handlers run in priority order
and return auditable receipts. The ledger retains ordered output, diff-based
replay records, and periodic constructor-form checkpoints. Execution is
deterministic from the same graph state and chosen edges; persisted semantic
journal playback across renderers is still being completed.

### Provisioning

Before a node is visited, the engine can proactively resolve its dependencies.
If a scene requires "a villain", the resolver searches for matching actors by
scope and compatibility, proposes candidates, and binds a valid match.

This mechanism acts as a constraint solver over the story graph: partial
requirements are resolved into concrete commitments at runtime.

### Interaction Models

StoryTangl supports multiple interaction styles over the same runtime contract:

- **Structured traversal**: authored episodes, scenes, blocks, and explicit
  choices.
- **Sandbox exploration**: dynamic projection of available actions from current
  state, including location links, present assets, fixtures, mobs, schedules,
  darkness, and inventory.
- **Client command adapters**: parser-like or command-bar input can match user
  text to the current choice surface without creating a second action model.

These modes lower to ordinary StoryTangl `Action` edges and execute through the
same VM phases, journal fragments, ledger history, and replay machinery.

### Extensibility

Story mechanics, world-specific rules, media systems, minigames, and sandbox
behaviors plug in as phase behaviors rather than alternate runtimes. A layered
dispatch cascade lets world authors override defaults without modifying core
code:

```text
SYSTEM -> APPLICATION -> DOMAIN -> INSTANCE -> INLINE
```

Sandbox traits such as `portable`, `lockable`, `openable`, `provides_light`,
and `requires_charge` are authoring compression. The compiler lowers them into
typed runtime facets, and phase handlers project ordinary actions from those
facets.

For a deeper treatment of the conceptual foundations, see
[docs/src/design/story/philosophy.md](docs/src/design/story/philosophy.md).

---

## Current Capability Status

StoryTangl is a working reference engine with several complete vertical proofs,
not a uniformly mature game-production stack. These categories describe the
current repository rather than the full design vocabulary.

### Realized Today

- One typed runtime compiles world bundles, materializes graphs, resolves
  dependencies, traverses the phase pipeline, persists ledgers, and emits one
  journal-fragment stream.
- Near-native YAML and a bounded Twee/Twine codec feed the same compiler and
  runtime. The sandbox and structured-story surfaces both lower interaction to
  ordinary `Action` edges.
- `ServiceManager` is the canonical lifecycle API. CLI and REST adapters, a Vue
  web client, and Ren'Py and pygame reference ports consume its typed responses;
  the non-web ports remain proofs of concept rather than supported products.
- Assembly, transactions, credentials, progression primitives, sandbox
  projection, and several game kernels are implemented. The `repartee_loop`
  world demonstrates retained repertoire, contest aftermath, prize-gated
  choices, attributed dialog, and two interchangeable art packs.
- File-backed media travels through world inventory, provisioning, journal
  fragments, service dereferencing, and client-neutral roles/staging hints. A
  ComfyUI-backed creator lifecycle and a separate receipt-based batch helper are
  also present; they do not form a second story runtime.
- Structured authoring diagnostics and world preflight endpoints exist, with
  focused validators continuing to grow through the same reporting surface.

### Live Integration Gaps

- Persisted semantic journal replay and exact cross-renderer fidelity
  ([#400](https://github.com/derekmerck/storytangl/issues/400)), plus real-browser
  acceptance over the REST/web stack
  ([#73](https://github.com/derekmerck/storytangl/issues/73)).
- World-scoped token dereferencing: catalogs are bounded, but `Token` can still
  fall through to a process-global singleton registry
  ([#404](https://github.com/derekmerck/storytangl/issues/404)).
- Media contract convergence: authored URL/data media bypasses the normal
  inventory path ([#407](https://github.com/derekmerck/storytangl/issues/407)),
  and staged visual elements still need one addressable piece/update/delete
  lifecycle instead of client-side identity inference
  ([#409](https://github.com/derekmerck/storytangl/issues/409)).
- Broader visual proof across distinct fragment surfaces, worlds, clients, and
  one out-of-process transport remains an integration milestone
  ([#410](https://github.com/derekmerck/storytangl/issues/410)).

### Aspirational Directions

Solver-backed narrative analysis, multi-reader traversal, cross-story
progression, semantic lifting/compression, broad authoring UX, and richer
generative presentation are research directions. Open issues and design notes
preserve those ideas, but they are not promises of current support or required
steps on the integration baseline.

The active sequencing boundary is the
[integration roadmap](https://github.com/derekmerck/storytangl/issues/402);
gameplay convergence and demonstrations are tracked separately in
[#332](https://github.com/derekmerck/storytangl/issues/332).

---

## Project Structure

```text
storytangl/
├── engine/
│   ├── src/tangl/              # Core engine package
│   │   ├── core/               # Timeless primitives: entity, graph, dispatch
│   │   ├── vm/                 # Temporal evolution: phases, traversal, replay
│   │   ├── story/              # Narrative semantics: episodes, concepts
│   │   ├── journal/            # Fragment and journal surfaces
│   │   ├── ir/                 # Intermediate representation models
│   │   ├── loaders/            # World bundles and source codecs
│   │   ├── mechanics/          # Optional domain vocabularies
│   │   ├── media/              # Media specs, creators, and dereference boundary
│   │   ├── prose/              # Text-facing parsing and voice helpers
│   │   ├── service/            # Manager-first lifecycle, auth, typed responses
│   │   └── persistence/        # Storage abstraction across backends
│   └── tests/                  # Engine test suite
├── apps/
│   ├── cli/                    # cmd2 command-line interface
│   ├── server/                 # FastAPI REST API
│   ├── web/                    # Vue 3 + TypeScript web client
│   ├── renpy/                  # Ren'Py proof-of-concept adapter
│   └── pygame/                 # Headless-tested visual reference port
├── docs/                       # Sphinx docs and design notes
├── worlds/                     # Reference story bundles
└── scripts/                    # Utility and analysis scripts
```

### Canonical References

Start with these:

- [AGENTS.md](AGENTS.md): contributor rules, coding style, layer boundaries.
- [ARCHITECTURE.md](ARCHITECTURE.md): cross-layer type map and invariants.
- [docs/src/design/story/philosophy.md](docs/src/design/story/philosophy.md):
  conceptual foundations.
- [docs/src/design/glossary.md](docs/src/design/glossary.md): vocabulary
  mapping between narratology and implementation.

Major package design notes:

| Layer | Design Doc | Scope |
|-------|------------|-------|
| core | [CORE_DESIGN.md](engine/src/tangl/core/CORE_DESIGN.md) | Entity, graph, dispatch, templates |
| vm | [VM_DESIGN.md](engine/src/tangl/vm/VM_DESIGN.md) | Phases, provisioning, traversal, replay |
| story | [STORY_DESIGN.md](engine/src/tangl/story/STORY_DESIGN.md) | Fabula compilation, concepts, journal |
| service | [SERVICE_DESIGN.md](engine/src/tangl/service/SERVICE_DESIGN.md) | Manager lifecycle, persistence, transport, typed responses |
| media | [MEDIA_DESIGN.md](engine/src/tangl/media/MEDIA_DESIGN.md) | Media inventory, creators, dereference boundary |
| sandbox | [SANDBOX_DESIGN.md](engine/src/tangl/mechanics/sandbox/SANDBOX_DESIGN.md) | Location-centered dynamic choice projection |

---

## Getting Started

### Prerequisites

- Python >= 3.12
- [Poetry](https://python-poetry.org/) for dependency management
- Node.js 18+ and Yarn for the web client

### Install

```bash
git clone https://github.com/derekmerck/storytangl.git
cd storytangl
poetry install
```

Optional extras:

```bash
poetry install -E server    # FastAPI + uvicorn + storage extras
poetry install -E cli       # cmd2 CLI only
poetry install -E docs      # Sphinx documentation extras
```

### Run Tests

```bash
# Configured repository suite: engine, docs, scripts, and reference adapters
poetry run pytest

# Engine suite only
poetry run pytest engine/tests

# Individual layers
poetry run pytest engine/tests/core
poetry run pytest engine/tests/vm
poetry run pytest engine/tests/story
poetry run pytest engine/tests/mechanics

# Web client
cd apps/web
yarn install
yarn test

# Pygame reference port
PYTHONPATH=engine/src:apps/pygame/src poetry run pytest apps/pygame/tests
```

### Run The Reference Apps

```bash
# CLI
poetry run tangl-cli

# REST server
poetry run tangl-serve
# then open http://localhost:8000/docs for the OpenAPI explorer

# Web client, with the server running
cd apps/web
yarn install
yarn dev
# then open http://localhost:5173

# Pygame reference port and the staged repartee world
PYTHONPATH=engine/src:apps/pygame/src:worlds/repartee_loop \
  poetry run python -m tangl.pygame_client --world repartee_loop
```

### Build Docs

```bash
poetry run make -C docs html
```

---

## Research Directions

StoryTangl is positioned as a research platform for computational narratology.
The following list is a research agenda, not a supported-feature list. Some
ideas have bounded pressure tests; most require a named consumer and a focused
contract before promotion:

- **Narrative planning as constraints**: dependency resolution, provisioning,
  and future fact-ledger solving.
- **Superposition of possible stories**: latent truth, observed disclosure,
  retcon, and payoff selection over a constrained design space.
- **Narrative shape space**: semantic distance metrics for comparing and
  interpolating story paths.
- **Proppian re-entrant patterns**: compressing interactive narratives through
  reusable morphological function templates.
- **Parametric discourse**: projecting the same fabula through different
  thematic vocabularies.
- **Multi-lane storytelling**: multiple navigators traversing shared fabula
  with distinct visibility, perspective, and decision policy.
- **Semantic story compression**: recovering the playable shape of existing IF
  and gamebook works through compact world facts plus reusable handlers.
- **Structural inference**: recovering approximate story graphs from existing
  IF corpora such as Twine, Ink, ChoiceScript, ZIL, and gamebook formats.

See the philosophy and package design notes for current status; some items are
implemented as pressure tests, while others remain research vocabulary.

---

## Contributing

Contributions are welcome. Read [AGENTS.md](AGENTS.md) before starting. The
most important rules are:

- Use concrete types and trust them.
- Respect layer boundaries: `core -> vm -> story -> service`.
- Prefer the existing primitives before inventing a new mechanism.
- Keep domain mechanics as clients of the architecture unless a design note
  explicitly promotes a concept into the engine kernel.
- Write or update focused tests for behavior changes.

Basic workflow:

1. Read `AGENTS.md` and the relevant `*_DESIGN.md`.
2. Create a feature branch.
3. Write or update tests.
4. Implement the change.
5. Verify with the relevant `poetry run pytest ...` command.
6. Open a PR with a clear description of what changed and why.

---

## Acknowledgments

StoryTangl has been in development since 2021 across roughly 38 architectural
iterations, from a gamebook parser to a narrative virtual machine. It draws on
the author's background in medical imaging, shape theory, signal processing,
high-dimensional optimization, and literary theory.

The theoretical foundations rest on work by Mieke Bal, Gérard Genette, Seymour
Chatman, Roland Barthes, Vladimir Propp, Espen Aarseth, Marie-Laure Ryan,
Emily Short, Chris Martens, and others whose ideas about narrative structure
turned out to be eminently computable.

Development has been significantly aided by AI coding agents, who serve as
tireless architectural reviewers and occasionally suggest things that are
actually good.

---

## Version History

For the compact project history, see [VERSIONS.md](VERSIONS.md).

---

## License

MIT. See [LICENSE](LICENSE) for details.
