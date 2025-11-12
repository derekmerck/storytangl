# StoryTangl Contributor Guide

Welcome! This project powers StoryTangl, an abstract narrative graph engine. Use this
file as the quick-reference guide for coding conventions, documentation tone, and the
core ideas you should understand before contributing.

## Repository layout
- `engine/src/tangl/`: primary Python package with the runtime engine and utilities.
- `engine/tests/`: canonical test suite (pytest based).
- `apps/` and `worlds/`: optional entry points and sample content; most engine work
  lives under `engine/src/tangl/`.
- `docs/`: Sphinx documentation sources; keep docstrings compatible with Sphinx.

## Coding style
- Target **Python 3.13** and enable postponed annotations with
  `from __future__ import annotations` in new modules when you need forward references.
- Use **type hints everywhere** (functions, methods, attributes). Prefer concrete
  collection types (`set[str]`, `list[int]`, etc.) and reuse shared aliases from
  `tangl.type_hints` when available.
- Engine models generally inherit from **`BaseModelPlus`** (see
  `tangl.utils.base_model_plus`) or other Pydantic models. Extending
  `BaseModelPlus` gives you uniform identifier handling, comparison, and reset
  semantics—use it for new persistent entities unless you have a strong reason not to.
- Keep imports explicit and grouped: standard library, third-party, then local.
  Avoid wildcard imports.
- Follow Black-like formatting (4-space indents, trailing commas where they aid
  diffs, double quotes by default). Keep lines under 100 characters when possible.
- Use the project logging conventions: acquire module-level loggers with
  `logging.getLogger(__name__)` and prefer structured messages over f-string
  interpolation inside log calls.
- Align with the architectural and naming guidance in
  `docs/source/contrib/coding_style.md`. The quick summary: keep mechanisms
  explicit, respect the layer boundaries (`core` → `vm` → `service` → `app` →
  `presentation`), favor small nouns and deterministic behavior, and document the
  curated API surface. Review the doc for deeper rationale, anti-patterns, and
  testing expectations.

## Docstrings and comments
- Write docstrings in **reStructuredText** so Sphinx can build narrative docs.
  - Follow the `Why / Key Features / API / (Notes / See also)` structure for
    public classes as described in `docs/source/contrib/docstring_style.md`.
    Include the signature headline, single-sentence summary, and curated API
    bullets; defer exhaustive method prose to autodoc.
  - Keep module docstrings terse unless they introduce multiple peer concepts.
    Subpackage `__init__` files should outline conceptual layers and design
    intent. See the doc for section header underlines, linking conventions, and
    guidance on enum or record docstrings.
  - Cross-reference other symbols with `:class:`, `:meth:`, and section anchors to
    match existing docs (`tangl/core/entity.py` is a good model).
- Use `"""` triple double quotes for docstrings. Keep commentary sentences inside
  docstrings; reserve inline comments for clarifying implementation details.

## Core abstractions to understand
- **Entity** (`tangl.core.entity.Entity`): canonical base class for graph-managed
  objects. Provides identifiers, tagging, and comparison semantics.
- **Registry** (`tangl.core.registry.Registry`): collection helper that indexes
  entities by identifiers and criteria. New collections should extend this or use it.
- **Graph** (`tangl.core.graph.Graph` and friends): manages nodes, edges, and
  subgraphs for narrative structure.
- **Record / StreamRegistry / Snapshot** (`tangl.core.record`): immutable runtime
  artifacts capturing story state and playback.
- **Fragments** (`tangl.core.BaseFragment`, `tangl.journal.content`): narrative
  output payloads that the UI or downstream systems consume.
- **Behavior & Dispatch** (`tangl.core.behavior`, `tangl.vm.dispatch`): behavior
  pipelines that wrap and sequence callable actions while auditing results.
- **Virtual Machine** (`tangl.vm`): Interpreter loop for evaluating and evolving 
  graph state.
- **Orchestrator** (`tangl.service.Orchestrator`): registers controller endpoints
  and hydrates `User`, `Ledger`, and `Frame` dependencies based on type hints.
  Applications should invoke controller logic via the orchestrator instead of the
  deprecated `ServiceManager`.

## Rendering Architecture
- See `tangl.story.runtime.render` for the two-stage rendering pipeline.
- See `tangl.story.episode.block` for the multi-handler JOURNAL pattern.
- Key principle: Pure text transformation (render) is separate from 
  fragment wrapping (domain nodes).

## Service layer workflow (v3.7+)
- Controllers live in `tangl.service.controllers` and expose orchestrated
  endpoints via `@ApiEndpoint.annotate`.
- Applications call `Orchestrator.execute("Controller.method", user_id=..., **params)`
  and receive raw engine objects or dictionaries; transport layers handle
  serialization.

When introducing new engine features, align them with these primitives instead of
creating parallel abstractions. Favor composition over inheritance unless extending
one of the above base types.

## Testing and quality checks
- Run `pytest engine/tests` (or `poetry run pytest engine/tests`) before submitting
  changes. Add targeted tests in the matching module-specific folder.
- Keep fixtures lightweight; prefer deterministic data seeded from `engine/tests` or
  sample YAML fixtures under `engine/tests/resources`.
- If you add CLI or REST surface changes, also update the relevant app/world tests
  when they exist.

## Documentation and storytelling assets
- Update Sphinx docs under `docs/` when you add public APIs or change behavior. The
  docs assume the terminology outlined above—reuse section titles and glossary entries.
- Content YAML files under `worlds/` and `engine/src/tangl/mechanics/**` provide data
  for tests and demos. Maintain schema consistency and keep narrative examples
  inclusive and lore-friendly.

## Miscellaneous guidelines
- Avoid try/except around imports. Feature-detect capabilities with optional imports
  only when the feature is genuinely optional; otherwise declare dependencies in
  `pyproject.toml`.
- Prefer `Path` objects from `pathlib` over raw strings when handling filesystem
  paths (see `tangl.config.cast_path`).
- Respect existing serialization hooks—use `model_dump`/`model_validate` from
  Pydantic instead of manual dict munging when possible.
- When adding enums or user-facing strings, sanitize labels via `sanitize_str` and
  respect identifier/tag casing conventions.

Thanks for contributing to StoryTangl!
