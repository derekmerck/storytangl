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

**Why**: Nodes are GraphItems, all graph items are defined as being attached to a graph.  They are inert without a graph, so just assign it at creation time.

---

## Dereferencing Without Registry

**Problem**: Records store `*_id` fields but have no `.graph` to resolve them.

```python
# ❌ Bug: record has no graph
record = stream.find_one(is_instance=Event)
entity = record.origin  # AttributeError: no 'origin' property

# ✅ Correct: pass registry explicitly
entity = record.origin(entity_registry)
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
```

**Why**: Destination and source are state properties, edges serve a semantic relationship purpose beyond linkage, the endpoints merely represent providers.

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

**Why**: This is intentional.  Use a proper 2-phase serialization layer that clearly distinguishes between structure/unstructure and flatten/unflatten for the target protocol.  Flatteners for various types (date-time, uuid, types) and backends (pickle, json, yaml, bson) are included in the `tangl.persistence` library.  For json in particular, you can just grab the serialize/deserialize hook classes from there if you insist on using your own data controller.

---

## xfail Tests in Release

**Problem**: Tests marked `xfail` or `skip` indicate incomplete features or known bugs.

**Rule**:  Since we use `xfail=strict`, inadvertently fixing a marked bug will result in an error, which indicates that the xfail can be lifted and associated issues should be reviewed and closed.

---

## Related Guides
- [Coding Style & Architecture](coding_style.md)
- [Docstring Conventions](docstring_style.md)