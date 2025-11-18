# Coding Style & Architecture (semantic)

> Reference implementation priorities: **correctness**, **clarity**, **composability**.
> Lower layers stay **generic & abstract**; domain/presentation live above clean interfaces.

## 0) North star
- Small, explicit mechanisms over clever magic.
- Deterministic and auditable: same inputs → same outputs; mutations become artifacts.

## 1) Layering & dependencies

```
core   (entities, registries, graph topology, records, dispatch, capability)
  ↑
vm     (phases, frame/context, planning, provisioning, events & replay, ledger)
  ↑
service (domains/adapters, IO ports, orchestration, media/presentation hints)
  ↑
app    (CLI, notebooks, integrations, demo scenarios)
  ↑
presentation (renderers, web/UI)
```

**Rules**
- One-way arrows; no imports up the stack.
- Lower layers define **data shapes + contracts**; upper layers implement **policies**.
- Cross-layer communication via **handlers** and **records**—not hidden globals.

## 2) Packages & modules
- **Package** for a new conceptual layer (`core`, `vm`, `service`).
- **Module** for cohesive micro-domains (`replay/event.py`, `planning/offer.py`).
- **Single-class module** is fine; keep module docstring to 1–3 lines or omit.

## 3) Class design
- **Nouns are small**: data-first + a few sharp methods.
- **Records are immutable**: `Event`, `Patch`, `Snapshot`, `Fragment`.
- **Hooks over overrides** where it improves clarity—use `_structure_post/_unstructure_post` to avoid mutual recursion.  
  *Alternate pattern allowed:* explicit `structure/unstructure` overrides with a clear base case and round-trip tests.


## 4) Data model & serialization
- Pydantic v2 models for entities and records.
- `Entity.structure(data)` is the factory; `unstructure()` emits a minimal, portable dict (class tag + uid).
- No implicit IO in models; persistence belongs to ledger/service.

## 4a) Type purity on attributes
- **Store types in their native form; serialize only at boundaries.**
  - Hash digests are `bytes`, not hex strings (`content_hash: bytes`).
  - UUIDs are `UUID` objects, not strings.
  - Datetimes are `datetime` objects, not ISO strings.
  - Entity types are Python `Type` objects, not fully‑qualified name strings.

- **Use Pydantic serializers for JSON/YAML output.**
  - Add `@field_serializer` for rich types needing string form (e.g., `bytes.hex()`).
  - Keep in‑memory types pure for comparisons, hashing, and fast operations.
  - Example: `content_hash: bytes` serializes to hex via a serializer, not by storing hex internally.

- **Expose convenience accessors when appropriate.**
  - Properties such as `.content_hash_hex` for logs/UI.
  - Validators accepting multiple input forms (hex string → bytes).
  - Registry/query helpers that accept either native or serialized representations.

- **Rationale.**
  - Faster operations: comparing `bytes`/`UUID` beats parsing strings.
  - Stronger type safety: mistakes surface at boundaries.
  - Lower overhead: avoid repeated `.hex()`/`str()` conversions in hot paths.
  - Clearer semantics: `obj_cls: Type[Entity]` expresses intent better than a string FQN.
  - Type objects are the native representation in Python; FQNs serve only as serialized forms.
  - Serialization is a boundary concern; runtime behavior should never pay for it.

## 5) Mutations & replay
- Plan → Project → Commit. Planning computes intent; commit applies and logs artifacts.
- Prefer event sourcing: snapshot + canonicalized patches.
- Receipts are the audit trail of runtime decisions.

## 6) Handlers & dispatch
- Handlers are entity-centric; dispatch orders by priority → registration → uid.
- Selection via `Selectable`/criteria; avoid hard-coded switches.
- Thin handler bodies, rich `JobReceipt`s for aggregation and audit.
- **Priority ordering**: Use `Priority` enum (not strings) for deterministic sort order.

## 7) Naming & API surface
- Canon: `Graph`, `Node`, `Edge`, `Subgraph`; `Record`, `Event`, `Patch`, `Snapshot`, `Fragment`; `Frame`, `Context`, `Ledger`; `Requirement`, `Offer`, `Provisioner`.
- Enum members UPPERCASE; phases are UPPERCASE.
- Curate public surface with `__all__`.

## 8) Extensibility & hooks
- Registries as extension points; publish `selection_criteria`.
- Template-driven provisioning; no hard-coded class awareness.
- Presentation hints are advisory; clients may ignore.

## 9) Errors & invariants
- Fail fast at boundaries (arity/role checks; policy validation).
- Exceptions include context (ids, labels, policy).
- No silent coercion.
- **Duplicate prevention**: `Registry.add()` raises `ValueError` if entity with same UUID already exists (unless same object reference).

## 10) Determinism & RNG
- `Context.rand` is seeded from `(graph.uid, cursor.uid, step)`.
- No time-based randomness in `core`/`vm`.

## 11) Performance posture
- Optimize query paths; accept small constants for clarity elsewhere.
- Canonicalization linear-ish; avoid n² passes.

## 12) Observability
- Prefer emitting a `Record` to logging when it affects reasoning.
- Minimal structured logs at orchestration edges.
- **Audit tracking**: Use `Entity.is_dirty` to flag non-reproducible mutations (forced jumps, direct eval/exec). Check `Registry.any_dirty()` to detect tainted state.

## 13) Tests (contracts > mechanics)
- Round-trip `structure/unstructure` for composites.
- Phase reducers return the documented shape.
- Provisioning policies enforce required fields.
- Event canonicalization removes redundant updates; replay reproduces state.
- Deterministic RNG in tests; monkeypatch randomness when needed.
- **No failing tests in releases**: Fix or remove all `xfail`/`skip` markers before shipping.

## 14) Anti-patterns
- Upward imports (lower layer depending on higher).
- Hidden globals/state; domain singletons leaking into `core`/`vm`.
- Recursive factories without a base case.
- Overgrown classes; mix responsibilities → extract helpers.
- Implicit IO in `core`/`vm`.

## 15) Dereferencing & Resolution Patterns

StoryTangl maintains strict separation between identity (UUIDs) and references (resolved objects). This enables serialization, event sourcing, and watched access patterns.

### GraphItems: Properties with Implicit Graph Access

**Rule**: GraphItems store `*_id: UUID` fields and provide properties that resolve via `.graph`.

**Pattern**:
```python
class Edge(GraphItem):
    source_id: Optional[UUID] = None
    destination_id: Optional[UUID] = None
    
    @property
    def source(self) -> Optional[Node]:
        """Resolve source node via graph registry (watched)."""
        return self.graph.get(self.source_id) if self.source_id else None
    
    @source.setter
    def source(self, node: Optional[Node]):
        self.source_id = node.uid if node else None
```

**Why**:
- Every access goes through `self.graph.get()` → `WatchedRegistry` can intercept
- Serialization clean: only `*_id` fields in dict
- Type hints work: property returns concrete type, field stores UUID

### Records: Methods with Explicit Registry Parameter

**Rule**: Records are frozen and graph-independent. They store `*_id: UUID` and require explicit registry for dereferencing.

**Pattern**:
```python
class Record:
    blame_id: Optional[UUID] = None
    
    def blame(self, registry: Registry[Entity]) -> Optional[Entity]:
        """Dereference blame_id via provided registry."""
        return registry.get(self.blame_id) if self.blame_id else None
```

**Why**:
- Explicit: caller must provide registry (matches frozen/independent constraint)
- No hidden state: can't cache because record is immutable
- Clear intent: "this requires a registry to resolve"

**Asymmetry is intentional**:
- GraphItems use properties (no args) because `.graph` is always present
- Records use methods (registry arg) because they're topology-independent

### Collections & Queries: Fresh Iterators

**Rule**: All query, filter, and resolution methods return **fresh iterators**, never cached collections.

**Pattern**:
```python
@property
def members(self) -> Iterator[GraphItem]:
    """Yield members by resolving member_ids via graph."""
    return (self.graph.get(uid) for uid in self.member_ids)

def edges_in(self, **criteria) -> Iterator[Edge]:
    """Yield incoming edges matching criteria."""
    return self.graph.find_edges(destination=self, **criteria)
```

**Why**:
- Consistency: all queries behave the same way
- Efficiency: no hidden allocations—caller decides materialization
- Freshness: always reflects current state (critical for `WatchedRegistry`)
- Type safety: `Iterator[T]` correctly typed

**Common gotcha**:
```python
# Iterator exhausts on first use
members = subgraph.members
print(list(members))  # [node1, node2]
print(list(members))  # [] - exhausted!

# Solution: materialize explicitly if multiple passes needed
members = list(subgraph.members)  # now reusable
```

**When to materialize**:
```python
# Single iteration: use iterator directly
for node in subgraph.members:
    process(node)

# Multiple iterations: materialize first
members = list(subgraph.members)
for node in members: ...
for node in members: ...  # works

# Debug logging: materialize to avoid exhaustion
members = list(subgraph.members)
logger.debug(f"Found {len(members)} members: {members}")
```

**Type hints**:
- Use `Iterator[T]` for single-use queries
- Use `Iterable[T]` if the result is reusable (rare in this codebase)
- Never use `list[T]` unless actually materializing

### No GraphItem → GraphItem Direct Pointers

**Rule**: GraphItems must not hold direct references to other GraphItems.

**Why**:
- Prevents circular references during serialization
- Enables `WatchedRegistry` to intercept all cross-item access
- Simplifies graph traversal and mutation tracking

**Enforcement**:
- Store only `*_id: UUID` fields
- Provide properties/methods that resolve via `.graph`
- Exclude `.graph` itself from serialization (`exclude=True`)

### Summary Table

| Context | Storage | Access Pattern | Registry Source | Caching |
|---------|---------|---------------|-----------------|---------|
| **GraphItem** | `other_id: UUID` | `@property other(self) -> T` | `self.graph` | No |
| **Record** | `other_id: UUID` | `def other(self, reg) -> T` | Explicit param | No (frozen) |
| **Query** | N/A | `def find_all() -> Iterator[T]` | `self` (registry) | No |

### Related Documentation
- See [Docstring Conventions](docstring_style.md) for how to document these patterns
- See `Entity.is_dirty` in Section 12 for audit tracking of non-reproducible state

---

## Related Guides
- [Docstring & Autodoc Conventions](docstring_style.md)
