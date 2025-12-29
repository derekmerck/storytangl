# Core Test Suite Refactoring Plan

## Objectives
1. Improve test coverage for all core components
2. Organize tests around key architectural concepts
3. Eliminate redundancy and duplication
4. Use concise, focused test functions with clear naming
5. Group related tests using classes for better organization

## Proposed Test Structure

### tests/core/
```
test_entity.py          - Entity: creation, identifiers, matching, tags, serialization
test_registry.py        - Registry: CRUD, search, filtering, serialization
test_singleton.py       - Singleton: uniqueness, registry, hashing, inheritance
test_content_addressable.py - ContentAddressable: hash computation, determinism

test_graph.py           - Graph, Node, Edge: basic topology and operations
test_graph_hierarchy.py - Subgraphs, parent chains, paths, nesting
test_token.py          - Token specialization
test_scope_selectable.py - Scope selection functionality

test_record.py         - Record, Snapshot, BaseFragment
test_stream_registry.py - StreamRegistry: bookmarks, channels

test_behavior.py       - Behavior, BehaviorRegistry, CallReceipt
test_layered_dispatch.py - LayeredDispatch functionality

test_dispatch.py       - core_dispatch integration tests
```

## Test Organization Pattern

Each test file should follow this structure:

```python
"""Tests for [module/concept]."""

# 1. Imports and test fixtures

# 2. Test classes grouping related functionality
class TestEntityCreation:
    """Tests for entity instantiation and initialization."""

class TestEntityIdentifiers:
    """Tests for entity identifiers (uid, label, get_label)."""

class TestEntityMatching:
    """Tests for entity.matches() functionality."""

class TestEntitySerialization:
    """Tests for unstructure/structure roundtrip."""
```

## Consolidation Strategy

### Phase 1: Entity Tests
- Merge test_entity.py, test_entity_2.py, test_entity_3.py, test_entity_aliasing_1.py, test_entity_aliasing_2.py
- Remove duplicate tests (e.g., test_has_tags variants)
- Organize into classes:
  - TestEntityCreation
  - TestEntityIdentifiers
  - TestEntityTags
  - TestEntityMatching
  - TestEntitySerialization
  - TestEntityEquality

### Phase 2: Singleton Tests
- Merge test_singleton_1.py, test_singleton_2.py, test_singleton_3.py
- Merge test_singleton_inheritance_1.py, test_singleton_inheritance_2.py, test_singleton_inheritance_3.py
- Organize into:
  - TestSingletonBasics
  - TestSingletonRegistry
  - TestSingletonInheritance
  - TestSingletonSerialization

### Phase 3: Graph Tests
- Merge test_graph.py, test_graph_1.py, test_graph_2.py, test_graph_3.py
- Separate hierarchy/subgraph tests into test_graph_hierarchy.py
- Keep test_node.py, test_edge.py, test_token.py focused
- Organize into:
  - TestGraphBasics
  - TestNodeOperations
  - TestEdgeOperations
  - TestGraphSerialization
  - TestSubgraphHierarchy
  - TestScopeSelection

### Phase 4: Registry Tests
- Consolidate registry tests
- Merge with test_selection.py if applicable
- Organize into:
  - TestRegistryBasics
  - TestRegistrySearch
  - TestRegistrySerialization

### Phase 5: New Test Coverage
- Create comprehensive test_behavior.py
- Create test_layered_dispatch.py
- Expand test_dispatch.py for dispatch hooks
- Create test_stream_registry.py

## Testing Principles

1. **One assertion per test** (when possible) - Makes failures clear
2. **Descriptive test names** - test_entity_matches_by_label_and_tags_combined
3. **DRY fixtures** - Shared setup in pytest fixtures
4. **Fast tests** - Avoid unnecessary complexity
5. **Clear organization** - Group by functionality, not by file size

## Success Metrics

- [ ] All test files follow consistent naming convention
- [ ] No test files numbered (no test_foo_2.py)
- [ ] All core modules have corresponding test coverage
- [ ] Test classes group related functionality
- [ ] Redundant tests removed
- [ ] Test count maintained or increased
- [ ] All tests pass after refactoring
