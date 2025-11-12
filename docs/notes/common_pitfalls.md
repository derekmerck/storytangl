# Common Pitfalls & Patterns

> Practical guide to avoiding subtle bugs in StoryTangl development.

## Iterator Exhaustion

**Problem**: Query results return fresh iterators, which exhaust after first use.

```python
# ❌ Bug: iterator exhausts after first loop
members = subgraph.members  # Iterator[GraphItem]
for m in members:
    print(m.label)  # Works

for m in members:
    print(m.label)  # Prints nothing - iterator exhausted!
```

**Solution**: Materialize explicitly when multiple passes needed.

```python
# ✅ Correct: materialize for reuse
members = list(subgraph.members)
for m in members:
    print(m.label)

for m in members:
    print(m.label)  # Still works
```

**When this happens**:
- `subgraph.members` → `Iterator[GraphItem]`
- `node.edges_in()` → `Iterator[Edge]`
- `registry.find_all(**criteria)` → `Iterator[Entity]`
- `node.ancestors()` → `Iterator[Subgraph]`

**Debug logging trap**:
```python
# ❌ Bug: logging exhausts iterator
edges = node.edges_out()
logger.debug(f"Edges: {list(edges)}")  # Exhausts iterator!
for e in edges:
    process(e)  # Never runs

# ✅ Correct: materialize once
edges = list(node.edges_out())
logger.debug(f"Edges: {edges}")
for e in edges:
    process(e)  # Works
```

---

## GraphItem Auto-Registration

**Problem**: GraphItems auto-register with their graph via `@model_validator`, which can cause confusion during testing.

```python
# Current behavior (surprising)
node = Node(label="test", graph=graph)
# node is now in graph.data automatically!

# Testing issue
node = Node(label="test")  # No graph
# Validation passes but node.graph is None
# Later access to node.parent crashes
```

**Workaround**: Always use `Graph.add()` for explicit attachment.

```python
# ✅ Explicit pattern
node = Node(label="test")
graph.add(node)  # Sets node.graph = self, then registers
```

**Future**: Consider removing auto-registration validator and making `Graph.add()` the only attachment point.

---

## Dereferencing Without Registry

**Problem**: Records store `*_id` fields but have no `.graph` to resolve them.

```python
# ❌ Bug: record has no graph
record = stream.find_one(record_type="event")
entity = record.blame  # AttributeError: no 'blame' property

# ✅ Correct: pass registry explicitly
entity = record.blame(entity_registry)
```

**Why**: Records are frozen and graph-independent by design (see [Section 15](coding_style.md#15-dereferencing--resolution-patterns)).

---

## Caching GraphItem Parent

**Problem**: `GraphItem.parent` uses `functools.cached_property`, which can become stale after reparenting.

```python
# Potential issue
node = Node(label="n", graph=g)
sg1.add_member(node)
parent1 = node.parent  # sg1

sg2.add_member(node)
parent2 = node.parent  # Still sg1 (cached!)

node._invalidate_parent_attr()  # Manual invalidation required
parent3 = node.parent  # Now sg2
```

**Mitigation**: Always call `._invalidate_parent_attr()` after reparenting (currently done in `Subgraph.add_member()`).

**Future**: Consider removing cache entirely or using explicit `_parent_cache` field.

---

## Edge Source/Destination Mutability

**Problem**: Edges allow reassigning `source` and `destination` after creation, which may break graph invariants.

```python
edge = g.add_edge(node1, node2)
edge.destination = node3  # Mutates in-place

# Is this intentional or should edges be immutable post-add?
```

**Current status**: Mutation is allowed but not clearly documented.

**Decision needed**: Either document mutation semantics or enforce immutability after `Graph.add()`.

---

## `is_dirty` Not Set Automatically

**Problem**: `Entity.is_dirty` is a flag, but nothing automatically sets it.

```python
# Manual marking required
entity.mark_dirty("Forced state mutation via eval()")

# Check at collection level
if registry.any_dirty():
    logger.warning("Graph contains non-reproducible mutations")
```

**Future**: Integrate with `WatchedRegistry` to auto-mark dirty on certain operations (eval, exec, forced jumps).

---

## Structure/Unstructure Recursion

**Problem**: Subclasses that override `structure()` can cause infinite recursion if not careful.

```python
# ❌ Bug: infinite recursion
class MyEntity(Entity):
    @classmethod
    def structure(cls, data):
        obj = super().structure(data)  # Calls Entity.structure
        # ... but Entity.structure may call MyEntity.structure
        return obj
```

**Correct pattern**: Just call super().structure(data) first to dereference the correct entity class. 

```python
# ✅ Correct: hook pattern
class MyEntity(Entity):
    @classmethod
    def structure(cls, data):
        foo = data.pop('foo', 0) + 1
        obj = super().structure(data)
        assert object.foo == foo
        return obj
```

**Applies to**: `_structure_post`, `_unstructure_post` hooks (see [Section 3](coding_style.md#3-class-design)).

---

## Missing Type Hints on Queries

**Problem**: Using `Iterable[T]` instead of `Iterator[T]` masks single-use semantics.

```python
# ❌ Vague: implies reusable
def members(self) -> Iterable[GraphItem]:
    return (self.graph.get(uid) for uid in self.member_ids)

# ✅ Precise: signals single-use
def members(self) -> Iterator[GraphItem]:
    return (self.graph.get(uid) for uid in self.member_ids)
```

**Rule**: Use `Iterator[T]` for all query methods that return generators.

---

## Channel Tag Convention

**Problem**: Channel filtering relies on `"channel:"` prefix convention, but it's not centralized.

```python
# Inconsistent usage
record1 = Record(type="event", tags={"channel:journal"})
record2 = Record(type="event", tags={"chan:journal"})  # Typo breaks filtering
```

**Solution**: Use centralized constant.

```python
# ✅ Correct: centralized
from tangl.core.record import CHANNEL_TAG_PREFIX


def channel_tag(name: str) -> str:
    return f"{CHANNEL_TAG_PREFIX}{name}"


record = Record(type="event", tags={channel_tag("journal")})
```

**Future**: Add `CHANNEL_TAG_PREFIX = "channel:"` constant to `record.py`.

---

## Serialization: `obj_cls` String vs Type

**Problem**: `unstructure()` emits `obj_cls` as a type, but some serializers expect strings.

```python
# Serialization may fail
data = entity.unstructure()
# data['obj_cls'] = <class 'MyEntity'>
json.dumps(data)  # TypeError: not JSON serializable
```

**Workaround**: Use a proper 2-phase serialization layer that clearly distinguishes between structure/unstructure and flatten/unflatten for the target protocol.  Flatteners for various types (date-time, uuid, types) and backends (pickle, json, yaml, bson) are included in the `tangl.persistence` library.  For json in particular, you can just grab the serialize/deserialize hook classes from there if you insist on using your own data controller.

---

## xfail Tests in Release

**Problem**: Tests marked `xfail` or `skip` indicate incomplete features or known bugs.

**Rule**: Reference releases should have **zero failing tests**.  For non-release versions, use `xfail` markers to track known bugs and `skip` to hide tests completely.  Since we use `xfail=strict`, inadvertently fixing a marked bug will result in an error, which indicates that the xfail can be lifted.

**Generally before release**:
1. Review all `xfail`/`skip` markers
2. Fix implementation to pass test, OR
3. Delete test if feature is not planned

---

## Related Guides
- [Coding Style & Architecture](coding_style.md)
- [Docstring Conventions](docstring_style.md)