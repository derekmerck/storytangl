# StoryTangl Contributor Guide

Welcome! This project powers StoryTangl, an abstract narrative graph engine.
Use this file as the quick-reference guide for design philosophy, coding
conventions, and the core ideas you should understand before contributing.

This is a **research platform and reference implementation**, not a production
SaaS product.  Code clarity, conceptual integrity, and ease of comprehension
are more important than robustness against hypothetical misuse.


## Design philosophy

These principles override all other guidance in this document.  When in doubt,
choose the option that leaves the code easier to read in five minutes.

### 1. Trust the types

StoryTangl has well-defined types at every layer.  Use them.

- **Do not `getattr` your way around typed interfaces.**  If a function
  receives a `PhaseCtx`, access `.graph` directly — do not write
  `getattr(ctx, "graph", None)`.  If the type is wrong, let it fail loudly.
- **Do not accept `Any` when a concrete type is known.**  `_ctx: Any` as a
  parameter type is a design smell.  Use the protocol (`VmPhaseCtx`,
  `VmResolverCtx`) or the concrete class (`PhaseCtx`).  If multiple context
  types are possible, use a `Union` or a shared protocol.
- **Do not add `isinstance` guards for types the caller is already required
  to provide.**  If a handler signature says `caller: TraversableNode`, do not
  begin the body with `if not isinstance(caller, TraversableNode): return`.
- **Use protocols for duck typing, not runtime probing.**  When a function
  genuinely needs to work with multiple unrelated types, define or reuse a
  `Protocol`.  Do not scatter `hasattr`/`getattr`/`callable(getattr(...))`
  probes through implementation code.

The only valid exception is interop boundaries where data arrives from
persistence, user input, or external systems with genuinely unknown shape.

### 2. Minimize cognitive overhead

Every line of code has a reading cost.  Minimize total cost.

- **Prefer direct expression over indirection.**  A 3-line function body is
  better than a 1-line call to a helper that exists nowhere else.
  Conversely, if you see the same 3-line stanza pasted in 5 places, extract
  it once and name it well.
- **Do not add layers "for flexibility."**  No abstract base class with one
  concrete subclass.  No strategy pattern with one strategy.  No registry
  when a dict suffices.  No factory when a constructor suffices.
  Add the abstraction *when the second use case arrives*, not before.
- **Do not write code to handle cases that cannot arise.**  If the graph
  always has a cursor during phase execution, do not write `if cursor is None:
  return`.  If a function is only called from one site and that site always
  passes a non-None value, do not guard against None.
- **Do not add compatibility shims preemptively.**  If a rename happens,
  update the callers.  A shim is warranted only when external consumers
  exist that you cannot update (e.g., persisted pickle references).

### 3. Reuse existing patterns

The codebase already has well-tested mechanisms.  Use them before inventing
alternatives.

- **Selector** is how you query entities.  Do not write bespoke filter loops.
- **BehaviorRegistry** and `chain_execute_all` is how you compose dispatch.
  Do not invent new plugin/hook registries.
- **`PhaseCtx.derive()`** is how you create a child context for a different
  cursor.  Do not manually pluck fields off a context to build another one.
- **EntityTemplate → materialize** is how you create runtime entities from
  authored data.  Do not bypass this with direct constructor calls unless the
  entity is genuinely ephemeral (like an `AnonymousEdge`).
- **`_DESIGN.md` files** in each subpackage describe the intended shape.
  Read the relevant design doc before adding a new module or public class.
  If your addition doesn't fit the described shape, discuss the mismatch
  before proceeding.

### 4. Keep layer boundaries sharp

```
Service  → Lifecycle, persistence, transport, access control
Story    → Narrative vocabulary, compilation, materialization, journal content
VM       → Phase pipeline, provisioning, traversal mechanics, replay
Core     → Timeless primitives: entity, registry, graph, selector, dispatch
```

- Import only downward.  Story may import VM and Core.  VM may import Core.
  Service may import all three.  **Never import upward.**
- If a function needs knowledge from a higher layer, accept it as a callback
  or protocol parameter — do not import the module.
- If you find yourself wanting to import `tangl.story` from `tangl.vm`, the
  feature belongs in story, not vm.  Move it.

### 5. Prefer deletion over annotation

If code is not used, delete it.  Do not comment it out.  Do not add a
`# deprecated` or `# legacy` marker and leave it.  `git` remembers.

- **No `# TODO: maybe...` on speculative features.**  File an issue or delete
  the comment.
- **No legacy compatibility shims without a documented consumer.**  If you
  cannot name the call site that needs the shim, the shim is dead code.
- **No accumulation of "just in case" parameters.**  If a parameter is always
  passed as `None` or `False`, remove it.

---

## Repository layout
- `engine/src/tangl/`: primary Python package with the runtime engine.
- `engine/tests/`: canonical test suite (pytest based).
- `apps/` and `worlds/`: optional entry points and sample content.
- `docs/`: Sphinx documentation sources.

## Coding style
- Target **Python 3.13**.  Use `from __future__ import annotations` for forward
  references.
- **Type hints everywhere.**  Prefer concrete types (`list[str]`, not
  `Iterable[Any]`).  Reuse aliases from `tangl.type_hints`.
- Engine models inherit from **`BaseModelPlus`** or other Pydantic models.
  Use it for new persistent entities unless you have a strong reason not to.
- Explicit, grouped imports: stdlib → third-party → local.  No wildcards.
- Black-like formatting: 4-space indents, trailing commas for diffs, double
  quotes.  Lines under 100 characters.
- Module-level loggers: `logging.getLogger(__name__)`.  Structured messages,
  no f-strings inside log calls.
- See `docs/src/contrib/coding_style.md` for deeper rationale.

## Docstrings and comments
- **reStructuredText** for Sphinx compatibility.
- Follow `Why / Key Features / API / Notes / See also` for public classes
  (see `docs/src/contrib/docstring_style.md`).
- Triple double quotes.  Commentary inside docstrings; inline comments only
  for implementation clarification.
- Do not write docstrings that merely restate the function signature.  If the
  name and types are self-explanatory, a one-line summary suffices.

## Core abstractions

These are the vocabulary of the engine.  Align new features with them instead
of creating parallel abstractions.

- **Entity** (`tangl.core.entity.Entity`): base for graph-managed objects.
- **Registry** (`tangl.core.registry.Registry`): indexed owning collection.
- **Graph** (`tangl.core.graph`): nodes, edges, subgraphs, hierarchy.
- **Selector** (`tangl.core.selector`): composable query predicates.
- **Behavior & Dispatch** (`tangl.core.behavior`, `tangl.vm.dispatch`):
  deterministic hook pipelines.
- **Record / StreamRegistry** (`tangl.core.record`): immutable ordered facts.
- **EntityTemplate** (`tangl.core.template`): authored prototypes, compiled
  then materialized.
- **Frame / Ledger** (`tangl.vm.runtime`): ephemeral pipeline driver and
  persistent cursor state.
- **Orchestrator** (`tangl.service`): endpoint dispatch with resource
  hydration.

## Service layer workflow
- Controllers in `tangl.service.controllers` expose endpoints via
  `@ApiEndpoint.annotate`.
- Callers use `Orchestrator.execute("Controller.method", ...)`.

## Testing
- Run `pytest engine/tests` before submitting changes.
- Use the poetry-managed venv.  Add test paths to `PYTHONPATH` if needed.
- Keep fixtures lightweight and deterministic.
- See `engine/tests/AGENTS.md` for detailed test conventions.

## Configuration
- Dynaconf via `tangl.config.settings` and `defaults.toml`.
- Paths under `[service.paths]` with `@path` casting.
- Read config through `tangl.config.settings` or its helpers.
- Do not introduce parallel settings systems.

### Media & Binary Assets (PNG / LFS safety)

StoryTangl uses Git LFS for `.png` and `.jpg` files.

1. **Never create PNG/JPG files inside the repository.**
2. **Use SVG primitives** for examples and test worlds.
3. **Create SVG files only in `tmp_path`** during tests, not in the repo.

## Miscellaneous
- No try/except around imports.  Declare dependencies in `pyproject.toml`.
- `Path` objects over raw strings for filesystem paths.
- Use `model_dump`/`model_validate`, not manual dict munging.
- If updating an implementation detailed in a `_DESIGN.md` doc, update the
  doc's status section so it does not go stale.
