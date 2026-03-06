# Story Entry Resolution

**Document Version:** 1.0  
**Status:** DESIGN ACCEPTED — not yet implemented on the current `tangl.story` / `tangl.service` runtime surface  
**Relevant layers:** `tangl.story.fabula`, `loaders`, `tangl.service`, `tangl.vm.runtime`

---

## Problem Statement

When a story graph is initialized, the starting cursor position is not always a
static property of the script. In anthology or carry-forward formats, the
correct entry passage may depend on a user's accumulated state across prior
stories.

The system needs a clean way to express this without:

- polluting `Ledger` with domain-specific routing logic
- requiring `RuntimeController` to know anthology conventions
- re-running the compiler or materializer for each user

---

## Resolution Priority Chain

Entry resolution is a two-stage process: compile-time default, then
init-time override.

### Stage 1 — Compile-time default (`StoryCompiler`)

Resolved once when the world is loaded and stored in
`StoryTemplateBundle.entry_template_ids`. Priority order:

1. Explicit `metadata.start_at` label or dotted path in the script
2. First template carrying an `is_start` annotation, either a locals field
   `{"start_at": True}` or the tag `{"start_at"}`
3. First leaf child of the first top-level group as a pure convention fallback

This phase is deterministic and context-free.

### Stage 2 — Init-time override (`World.create_story`)

Called once per story initialization, after materialization and before
`StoryInitResult` is returned. The world may inspect a caller-provided
namespace and substitute a different `initial_cursor_id` on the runtime graph.

The override returns a node uid or `None`. `None` means "accept the compiled
default."

---

## Namespace Contract

The intended API shape is for `World.create_story` to accept an optional
`namespace` argument:

```python
def create_story(
    self,
    story_label: str,
    *,
    init_mode: InitMode = InitMode.EAGER,
    namespace: dict | None = None,
) -> StoryInitResult:
```

The caller passes `{"user": User}` at minimum. Resolver logic may then inspect
domain-specific state such as carried flags, stats, or achievements without the
engine imposing a schema on user locals.

The intended caller is the service runtime controller, which already holds the
`User` object at story-creation time.

---

## World Implementation Sketch

```python
def create_story(
    self,
    story_label: str,
    *,
    init_mode: InitMode = InitMode.EAGER,
    namespace: dict | None = None,
) -> StoryInitResult:
    materializer = StoryMaterializer()
    result = materializer.create_story(
        bundle=self.bundle,
        story_label=story_label,
        init_mode=init_mode,
        world=self,
    )

    if namespace is not None:
        override_uid = self._resolve_entry_override(result.graph, namespace)
        if override_uid is not None:
            result.graph.initial_cursor_id = override_uid

    return result

def _resolve_entry_override(
    self,
    graph: StoryGraph,
    namespace: dict,
) -> UUID | None:
    return None
```

---

## Domain Registration Pattern

Anthology logic should live entirely in the domain package, not in the engine.
One plausible shape is a world subclass or registry-backed override hook:

```python
class AnthologyWorld(World):
    _ENTRY_RESOLVERS: dict[str, Callable] = {}

    @classmethod
    def register_entry_resolver(cls, story_key: str):
        def decorator(fn):
            cls._ENTRY_RESOLVERS[story_key] = fn
            return fn
        return decorator

    def _resolve_entry_override(self, graph, namespace):
        resolver = self._ENTRY_RESOLVERS.get(self.label)
        if resolver is not None:
            return resolver(graph, namespace)
        return None
```

This keeps story-specific routing rules opaque to the engine.

---

## Ledger Role

`Ledger` is intentionally passive with respect to entry resolution. It receives
`initial_cursor_id` from the graph and treats it as authoritative:

```python
ledger = Ledger.from_graph(
    graph=story_graph,
    entry_id=story_graph.initial_cursor_id,
)
```

This preserves the separation of concerns: graph initialization decides entry;
ledger owns traversal state after initialization.

---

## Design Constraints

- No recompilation per user: the override mutates only the per-story runtime
  graph returned from `create_story`.
- No ledger mutation: the ledger is initialized after override has already been
  applied.
- Domain logic stays in the domain package: `World` and service controllers
  expose only the seam.
- Namespace shape stays open: `{"user": User}` is the minimum useful contract.
- Compile-time default is always present: a missing resolver is not an error.

---

## Current Implementation Status

The current `tangl.story` runtime already supports compile-time entry
resolution through `StoryTemplateBundle.entry_template_ids` and graph-level
`initial_cursor_id` assignment during materialization.

The init-time override hook described here is still aspirational on the current
v38 surface:

- `World.create_story(...)` does not yet accept `namespace`
- `RuntimeController.create_story(...)` does not yet pass such a namespace
- no `_resolve_entry_override(...)` seam exists on `World`

This document should therefore be read as an accepted future design rather than
as a description of current behavior.

---

## Related

- `tangl.story.fabula.world.World.create_story`
- `tangl.story.fabula.materializer.StoryMaterializer`
- `tangl.story.fabula.compiler.StoryCompiler`
- `tangl.service.controllers.runtime_controller.RuntimeController.create_story`
- `docs/src/design/story/compilers.rst`
