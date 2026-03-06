# Replay Architecture — Patches, Step Records, and Reconstruction

## Context

The VM phase pipeline has two mutation windows bracketing the journal:

```
UPDATE    → pre-effects   → mutations that JOURNAL renders against
JOURNAL   → render        → consumes namespace with pre-effects applied
FINALIZE  → post-effects  → mutations that JOURNAL described happening
```

This document specifies how replay, rollback, and re-rendering work, and
why single-phase patches are sufficient for MVP.


## Existing Infrastructure

### Patch (vm38/replay/patch.py)

`Patch(Record)` already captures:

- `registry_id: UUID` — which registry this patch applies to
- `initial_registry_value_hash: bytes` — hash guard before application
- `final_registry_value_hash: bytes` — hash guard after application
- `events: list[Event]` — ordered CRUD operations on registry items

`Patch.apply(registry)` validates the initial hash, applies events, then
validates the final hash.  This provides built-in determinism verification:
if the hash doesn't match, something went wrong.

### RegistryObserver (vm38/replay/observer.py)

`RegistryObserver` captures `initial_value_hash` at construction, collects
events via `submit_event()`, and builds a `Patch` at `get_patch()` time
using the registry's current hash as the final hash.

### Key Insight

The initial/final hash pair on each Patch already provides the verification
story.  Re-execute from a checkpoint, apply the patch, check the final hash.
Mismatch means non-determinism.  No additional checksum mechanism needed.


## Two Streams, One Story

Replay depends on two distinct streams, neither sufficient alone:

### Decision Trace (Ledger)

Records *where the player went* and *how*:

```python
@dataclass
class StepRecord:
    step: int
    edge_id: Optional[UUID]          # None for goto/init/anonymous edges
    cursor_id: UUID                  # where the cursor landed
    entry_phase: ResolutionPhase     # where the pipeline started
    was_choice: bool                 # True = player chose, False = redirect

    patch: Optional[Patch]           # combined mutations (UPDATE + FINALIZE)
    state_hash: bytes                # graph value_hash after step completes
```

- `edge_id` identifies the specific edge followed, not just the destination.
  Two edges can lead to the same node; the edge may carry metadata
  (return_phase, trigger_phase) that affects pipeline behavior.
- `was_choice` distinguishes player-initiated moves from automatic redirects.
- `state_hash` is the graph's `value_hash()` after the full pipeline
  completes (both mutation windows applied).  This is the same hash
  stored as `final_registry_value_hash` on the patch.

### Narrative Trace (Ledger.output_stream)

Records *what the player saw*:

- **Fragments** — rendered journal output (text, choices, concept descriptions).
  Ordered by step.  These are stored Records in the output stream.


## Reconstruction Modes

### 1. Rollback to Step N

**Goal**: restore graph state to step N, discard everything after.

**Method**: load the most recent snapshot at or before step N, apply patches
forward from there.

```python
snapshot = find_snapshot_before(step_n)
graph = Graph.structure(snapshot.payload)
for step in step_history[snapshot.step : step_n]:
    if step.patch:
        step.patch.apply(graph)
```

The output stream is trimmed by tombstoning fragments after step N.
From there, the player can make a different choice and the pipeline
executes deterministically from the new graph state.

**Requires**: step_history with patches, snapshots at intervals.

### 2. Narrative Replay (playback)

**Goal**: reproduce the exact narrative the player experienced.

**Method**: emit stored fragments in order.  Patches optional (for state
verification) but not required — the fragments are already stored.

```python
for step in step_history:
    emit(output_stream.range(step.fragment_range))
```

**Requires**: output stream with fragments.

### 3. Re-Rendering Replay (transformation)

**Goal**: re-execute the journal with different handlers (vocabulary,
voice, perspective, language) while preserving the same story structure.

**Method**: rollback to step 0 (or a snapshot), re-execute the full
pipeline at each step with new journal handlers.  The pipeline is
deterministic — UPDATE produces the same intermediate state, JOURNAL
renders against it with new handlers, FINALIZE applies the same
post-effects.

```python
graph = Graph.structure(genesis_snapshot)
for step in step_history:
    edge = graph.get(step.edge_id) or AnonymousEdge(successor=graph.get(step.cursor_id))
    frame = Frame(graph=graph, cursor=current_cursor)
    frame.follow_edge(edge)  # full pipeline with new journal handlers
```

**Requires**: step_history (for edge/cursor sequence), genesis snapshot
(or snapshot + patches to rebuild state), registered journal handlers.

**Why this works without dual-phase patches**: re-execution runs the
actual pipeline code.  UPDATE creates intermediate state (conjured sword
exists), JOURNAL renders against it, FINALIZE cleans up.  The intermediate
state exists naturally during execution — it doesn't need to be stored
separately.


## Patch Canonicalization

With a single combined patch per step, canonicalization is straightforward:

- Collapse redundant mutations: `set(x, 1); set(x, 2)` → `set(x, 2)`
- Cancel inverses: `create(node); delete(node)` → no-op
- Merge creates: `create(node); set(node.label, "foo")` → `create(node, label="foo")`

This is noted as a future optimization in the existing Patch code.

The conjured sword case (create in UPDATE, reference in JOURNAL, delete in
FINALIZE) canonicalizes to no-op in the combined patch.  This is correct —
the sword never existed from the graph's final perspective.  And it's fine
because re-rendering doesn't use stored patches; it re-executes the pipeline
where the sword exists naturally during the UPDATE→JOURNAL window.


## Deferred: Dual-Phase Patches

### The Idea

Split each step's patch into `pre_patch` (UPDATE mutations) and `post_patch`
(FINALIZE mutations), with the journal sandwiched between.  This would enable
re-rendering from stored patches without re-executing UPDATE/FINALIZE handlers:

```python
apply(step.pre_patch)           # intermediate state from storage
fragments = re_render_journal() # new handlers, stored intermediate state
apply(step.post_patch)          # final state from storage
```

### Why It's Deferred

The clear use case — re-rendering without handler re-execution — requires
that the intermediate state be reconstructable from patches alone.  But:

1. **Re-execution is available and deterministic.**  If you have the handlers
   (which you do for any installed story), re-execution is simpler and
   doesn't require storing twice as many patches.

2. **The only case where you DON'T have the handlers** is export/transpilation
   to a system that doesn't have StoryTangl installed.  That's a real use
   case (the "Pandoc for IF" vision) but it's post-MVP and there may be
   better solutions — like exporting namespace snapshots or pre-rendered
   template contexts rather than raw patches.

3. **Canonicalization becomes fragile.**  Dual-phase patches must never
   canonicalize across the phase boundary (the conjured sword must survive
   in pre_patch even though post_patch deletes it).  This is a correctness
   constraint that's easy to violate and hard to test.

4. **Storage cost doubles** for marginal benefit in the common case.

### When to Revisit

Dual-phase patches become relevant when:

- Multi-lane stories where multiple players share a graph and need to
  reconstruct each other's intermediate states without re-executing
  each other's handlers.
- Export/transpilation pipelines that need handler-free reconstruction
  of journal-time state.
- Debugging tools that want to inspect intermediate state without
  setting breakpoints in handler code.

If any of these become real requirements, the pipeline already has the
natural split point (UPDATE/FINALIZE boundary), and the RegistryObserver
can snapshot at two moments instead of one.  The architectural change
is small; it's the canonicalization rules that need care.

### Canonicalization Rules (for future reference)

If dual-phase patches are implemented:

- **Within a single patch** — canonicalize freely.
- **Across patches** — NEVER canonicalize.  A create in pre_patch and a
  delete in post_patch both survive.
- **Combined patch** (derived, for state-only use) — canonicalize freely.
  This is a computed view, not a stored artifact.


## Implementation Status (MVP)

- [x] Patch with initial/final hash guards (vm38/replay/patch.py)
- [x] Event CRUD operations with registry application
- [x] Frame has dual mutation windows (UPDATE before JOURNAL, FINALIZE after)
- [x] Pipeline is deterministic (seeded RNG on PhaseCtx)
- [x] Graph diff implementation in `DiffReplayEngine.build_delta()`
- [x] StepRecord definition and population
- [x] Rollback implementation
- [x] Snapshot cadence hook (`checkpoint_cadence`) at choice boundaries
- [x] Step timeline persistence via StepRecords in `Ledger.output_stream`
- [ ] `_structured_hash` on Unstructurable (birth hash at structure/init time)
- [ ] Compositional graph hash from member hashes
- [ ] Copy-on-write graph for pipeline execution
- [ ] Re-rendering replay driver
- [ ] Patch canonicalization (optimization)

### Superseded

The following legacy components are replaced by the birth-hash + graph-diff
approach and can be removed:

- `vm38/replay/observer.py` — `RegistryObserver` (replaced by `diff_graphs`)
- `WatchedRegistry` concept — no longer needed, no mutation interception
- `ObservedEntity` concept — no longer needed, no proxy wrappers


## Open Questions

- **Snapshot frequency**: every step is safe but expensive.  Every N steps
  means rollback to arbitrary step requires patch replay from last snapshot.
  Snapshotting on player choice (not on redirects) might be the right
  heuristic — those are the decision points worth rolling back to.

- **Patch granularity**: field-level deltas vs. entity-level snapshots.
  The existing Event model supports field-level (`item_id` + `field` + `key`),
  which is compact but requires the Observer to track individual mutations.
  Decision already made in existing code; just needs wiring.

- **Output stream as patch target**: fragments are Records in an
  OrderedRegistry.  Should the output stream have its own patch (for
  tombstoning on rollback), or is trimming by step index sufficient?

- **Patch construction strategy — birth hash + graph diff**:

  The original WatchedRegistry/ObservedEntity approach intercepts every
  mutation through proxy wrappers — hundreds of lines of subtle proxy code
  that must handle every collection type and mutation pattern.  A simpler
  approach emerges from two observations:

  1. `structure()` already has the unstructured data in hand.  Hash it and
     stash it on the entity as `_structured_hash` at zero extra cost.

  2. PhaseCtx operates on a *copy* of the graph.  The original is pristine.

  This enables a pure diff approach:

  ```python
  def diff_graphs(original: Graph, mutated: Graph) -> Optional[Patch]:
      events = []
      orig_uids, mut_uids = set(original.keys()), set(mutated.keys())

      for uid in orig_uids - mut_uids:              # removed
          events.append(Event(operation=DELETE, key=uid))
      for uid in mut_uids - orig_uids:              # added
          events.append(Event(operation=CREATE,
                              value=mutated.get(uid).unstructure()))
      for uid in orig_uids & mut_uids:              # changed?
          entity = mutated.get(uid)
          if entity.value_hash() != entity._structured_hash:
              before = original.get(uid).unstructure()
              after = entity.unstructure()
              events.extend(_diff_to_events(uid, before, after))

      return Patch(..., events=events) if events else None
  ```

  **Cost profile**: for unchanged entities (the vast majority), one
  `value_hash()` call compared against stored bytes.  For changed entities,
  one `unstructure()` on the original + deepdiff.  Membership is a set
  difference.  No interception, no proxies, no key-path tracking.

  **Graph-level hash**: compositional from member hashes rather than full
  unstructure.  `graph.value_hash() = hashing_func(own_fields,
  sorted(member._structured_hash for ...))`.  Changes iff membership or
  any member's value changes.

  **Birth hash as general utility**: `_structured_hash` is useful beyond
  patching — dirty checking for serialization, cache invalidation, debug
  assertions.  Worth making a first-class property on Unstructurable.

  **Copy semantics**: the pipeline copy must be a deep copy.  Shallow copy
  shares entity objects, so mutating locals on the copy would mutate the
  original.  If the pipeline fails, discard the copy.  If it succeeds,
  the copy becomes canonical and the diff produces the patch.

  **Replaces**: `WatchedRegistry`, `ObservedEntity`, and most of the
  proxy machinery in `vm38/replay/observer.py`.  Total implementation is
  ~80 lines + a deepdiff dependency.
