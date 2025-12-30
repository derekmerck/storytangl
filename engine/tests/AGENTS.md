# Testing Guidelines for StoryTangl Engine

This document provides guidelines and best practices for writing and organizing tests in the StoryTangl engine, specifically tailored for AI coding agents and human developers.

## Core Principles

### 1. Organization by Concept, Not by File Size

Tests should be organized around **architectural concepts**, not implementation details or arbitrary file sizes.

**Good:**
```
tests/core/
├── entity/test_entity.py          # All Entity functionality
├── singleton/test_singleton.py    # All Singleton functionality
└── graph/test_graph.py            # Core graph operations
```

**Bad:**
```
tests/core/
├── test_entity_1.py
├── test_entity_2.py
├── test_entity_misc.py
```

### 2. Systematic Coverage

Each test module should comprehensively cover its concept:

- ✅ **Basic functionality** - Happy path scenarios
- ✅ **Edge cases** - Boundary conditions, empty inputs, None values
- ✅ **Error handling** - Invalid inputs, expected exceptions
- ✅ **Serialization** - Roundtrip testing (unstructure/structure, pickle)
- ✅ **Integration** - How the concept interacts with related concepts

### 3. Conciseness and Parsimony

- **Eliminate duplication** - No `test_foo`, `test_foo2`, `test_foo3`
- **One concept per test** - Focus each test on a single behavior
- **Minimal setup** - Only create what's needed for the test
- **Clear assertions** - Make failures easy to diagnose

## Test File Structure

Every test file should follow this pattern:

```python
"""Tests for [module.concept]

Organized by functionality:
- [Feature 1]: [description]
- [Feature 2]: [description]
- [Feature 3]: [description]
"""
from __future__ import annotations

# Standard library imports
import pickle
import pytest
from uuid import UUID

# Project imports
from tangl.core import Entity, Registry


# ============================================================================
# Test Fixtures and Helper Classes
# ============================================================================

class Person(Entity):
    """Test entity with person attributes."""
    name: str
    age: int


@pytest.fixture
def sample_registry():
    """Fixture providing a pre-populated registry."""
    reg = Registry()
    reg.add(Person(label="alice", name="Alice", age=30))
    return reg


# ============================================================================
# [Feature 1]
# ============================================================================

class Test[Feature1]:
    """Tests for [feature 1 description]."""

    def test_basic_case(self):
        """Test basic/happy path behavior."""
        pass

    def test_edge_case(self):
        """Test boundary conditions."""
        pass

    def test_error_handling(self):
        """Test expected error conditions."""
        pass


# ============================================================================
# [Feature 2]
# ============================================================================

class Test[Feature2]:
    """Tests for [feature 2 description]."""
    pass
```

### Key Elements:

1. **Module docstring** - Describes what's being tested and how it's organized
2. **Section markers** - Clear visual separation using `# ===...===`
3. **Helper classes** - Test entities at the top, NO "Test" prefix
4. **Fixtures** - Shared setup and teardown
5. **Test classes** - Group related tests by functionality
6. **Descriptive names** - Clear, specific test and class names

## Naming Conventions

### Test Functions

Use descriptive names that indicate **what** is being tested and **under what conditions**:

```python
# Good
def test_entity_matches_by_label_and_tags_combined()
def test_registry_find_returns_none_when_not_found()
def test_singleton_raises_error_on_duplicate_label()

# Bad
def test_matches()
def test_find()
def test_error()
def test_1()
```

### Test Classes

Use `Test<Concept><Aspect>` pattern:

```python
# Good
class TestEntityCreation:
    """Tests for entity instantiation and initialization."""

class TestEntityMatching:
    """Tests for entity.matches() functionality."""

class TestRegistrySearch:
    """Tests for Registry.find_all() and find_one()."""

# Bad
class TestEntity:  # Too broad
class TestStuff:   # Not descriptive
class TestEntity1: # Numbered
```

### Helper Classes

Test helper classes should NOT have "Test" prefix:

```python
# Good - pytest won't try to collect these
class Person(Entity):
    name: str

class Character(Entity):
    level: int

# Bad - pytest will try to collect these
class TestPerson(Entity):
    name: str
```

## Test Organization Patterns

### Grouping Tests

Group tests into classes by **what they test**, not by how they're implemented:

```python
# Good: Organized by functionality
class TestEntitySerialization:
    """Tests for entity serialization and deserialization."""

    def test_unstructure_basic(self):
        pass

    def test_structure_roundtrip(self):
        pass

    def test_pickle_roundtrip(self):
        pass


# Bad: Organized arbitrarily
class TestEntityMisc:
    """Miscellaneous entity tests."""

    def test_pickle(self):
        pass

    def test_matching(self):
        pass

    def test_creation(self):
        pass
```

### Progressive Complexity

Order tests from simple to complex:

```python
class TestEntityMatching:
    """Tests for entity.matches() functionality."""

    # Basic cases first
    def test_matches_by_label(self):
        """Test simple label matching."""
        pass

    def test_matches_by_single_tag(self):
        """Test matching a single tag."""
        pass

    # Then more complex cases
    def test_matches_with_multiple_criteria(self):
        """Test matching with multiple conditions."""
        pass

    def test_matches_with_callable_predicate(self):
        """Test matching with custom predicate."""
        pass

    # Finally edge cases
    def test_matches_with_missing_attribute(self):
        """Test matching when attribute doesn't exist."""
        pass
```

## Writing Clear Tests

### One Assertion Focus

Each test should verify one specific behavior:

```python
# Good: Tests one specific thing
def test_entity_label_sanitization(self):
    """Test that labels are sanitized (spaces removed)."""
    e = Entity(label="test label")
    assert e.label == "test_label"

# Acceptable: Multiple assertions for same concept
def test_entity_has_tags_with_multiple_tags(self):
    """Test has_tags() with multiple tag arguments."""
    e = Entity(tags={'a', 'b', 'c'})
    assert e.has_tags('a')
    assert e.has_tags('a', 'b')
    assert e.has_tags('a', 'b', 'c')

# Bad: Testing unrelated things
def test_entity_stuff(self):
    """Test entity stuff."""
    e = Entity(label="test label")
    assert e.label == "test_label"
    assert e.uid is not None
    assert len(e.tags) == 0
    assert e.matches(label="test_label")
```

### Minimal Setup

Only create what you need:

```python
# Good: Minimal setup
def test_entity_matches_by_label(self):
    e = Entity(label="hero")
    assert e.matches(label="hero")

# Bad: Unnecessary complexity
def test_entity_matches_by_label(self):
    reg = Registry()
    e1 = Entity(label="hero", tags={"magic", "fire"})
    e2 = Entity(label="villain", tags={"dark"})
    reg.add(e1)
    reg.add(e2)
    assert e1.matches(label="hero")
```

### Clear Failure Messages

Help debugging with clear assertions:

```python
# Good: Clear failure context
def test_child_inherits_parent_values(self):
    base = Character(label="base", hp=100)
    child = Character(label="child", from_ref="base")
    assert child.hp == 100, "Child should inherit hp from base"

# Acceptable: Assertion is self-evident
def test_child_inherits_parent_values(self):
    base = Character(label="base", hp=100)
    child = Character(label="child", from_ref="base")
    assert child.hp == 100
```

## Fixtures and Helpers

### Use Fixtures for Shared Setup

```python
@pytest.fixture
def populated_registry():
    """Fixture providing a registry with test entities."""
    reg = Registry()
    reg.add(Entity(label="a", tags={"x"}))
    reg.add(Entity(label="b", tags={"y"}))
    return reg


def test_registry_find_by_label(populated_registry):
    result = populated_registry.find_one(label="a")
    assert result is not None
    assert result.label == "a"
```

### Cleanup After Tests

Always clean up shared state:

```python
@pytest.fixture(autouse=True)
def clear_singletons():
    """Clear singleton registries before and after each test."""
    Singleton.clear_instances()
    yield
    Singleton.clear_instances()
```

### Helper Classes

Define test-specific entity classes at module level:

```python
# At top of file
class Person(Entity):
    """Test entity with person attributes."""
    name: str
    age: int


class Character(Entity):
    """Test entity for game characters."""
    level: int = 1
    hp: int = 100


# In tests
def test_person_matching():
    p = Person(name="Alice", age=30)
    assert p.matches(name="Alice")
```

## Common Patterns

### Testing Errors

```python
def test_registry_get_raises_on_string_label(self):
    """Test that get() raises helpful error for string argument."""
    reg = Registry()
    with pytest.raises(ValueError) as exc_info:
        reg.get("some_label")
    assert "find_one(label='some_label')" in str(exc_info.value)
```

### Testing Serialization

```python
def test_entity_unstructure_structure_roundtrip(self):
    """Test full serialization roundtrip."""
    original = Person(label="alice", name="Alice", age=30)

    # Unstructure to dict
    data = original.unstructure()
    assert isinstance(data, dict)
    assert "obj_cls" in data

    # Structure back
    restored = Entity.structure(data)
    assert isinstance(restored, Person)
    assert restored == original
```

### Testing Collections

```python
def test_registry_all_labels(self):
    """Test getting all entity labels."""
    reg = Registry()
    reg.add(Entity(label="a"))
    reg.add(Entity(label="b"))
    reg.add(Entity(label=None))  # Should be excluded

    labels = reg.all_labels()
    assert {"a", "b"}.issubset(labels)
    assert None not in labels
```

### Parametrized Tests

Use for testing similar scenarios with different inputs:

```python
@pytest.mark.parametrize("field,base_val,child_val", [
    ("hp", 100, 150),
    ("level", 1, 5),
    ("name", "Base", "Child"),
])
def test_inheritance_override(field, base_val, child_val):
    """Test that child can override inherited values."""
    base = Character(label="base", **{field: base_val})
    child = Character(label="child", from_ref="base", **{field: child_val})
    assert getattr(child, field) == child_val
```

## Anti-Patterns to Avoid

### ❌ Numbered Test Files

```python
# Bad
tests/core/test_entity_1.py
tests/core/test_entity_2.py
tests/core/test_entity_misc.py

# Good
tests/core/entity/test_entity.py
tests/core/entity/test_entity_advanced.py  # If truly needed
```

### ❌ Numbered Test Functions

```python
# Bad
def test_has_tags():
def test_has_tags2():
def test_has_tags3():

# Good
def test_has_tags_single():
def test_has_tags_multiple():
def test_has_tags_with_set():
```

### ❌ Testing Multiple Unrelated Things

```python
# Bad
def test_entity():
    e = Entity(label="test")
    assert e.label == "test"
    assert e.uid is not None
    assert e.matches(label="test")
    assert not e.has_tags("nonexistent")

# Good - Split into focused tests
def test_entity_label():
    e = Entity(label="test")
    assert e.label == "test"

def test_entity_has_uuid():
    e = Entity()
    assert e.uid is not None
```

### ❌ Unclear Test Names

```python
# Bad
def test_1():
def test_stuff():
def test_it_works():

# Good
def test_singleton_raises_error_on_duplicate_label():
def test_registry_find_one_returns_first_match():
def test_entity_matches_with_callable_predicate():
```

## Running Tests

### Run all tests
```bash
pytest engine/tests/
```

### Run specific module
```bash
pytest engine/tests/core/entity/
```

### Run specific test class
```bash
pytest engine/tests/core/entity/test_entity.py::TestEntityMatching
```

### Run specific test
```bash
pytest engine/tests/core/entity/test_entity.py::TestEntityMatching::test_matches_by_label
```

### Run with coverage
```bash
pytest engine/tests/ --cov=engine/src/tangl --cov-report=term-missing
```

### Run with verbose output
```bash
pytest engine/tests/ -v
```

## File Organization

Tests should mirror the source structure:

```
engine/
├── src/tangl/
│   ├── core/
│   │   ├── entity.py
│   │   ├── registry.py
│   │   └── singleton.py
│   └── ir/
│       └── base_script_model.py
└── tests/
    ├── core/
    │   ├── entity/test_entity.py
    │   ├── registry/test_registry.py
    │   └── singleton/test_singleton.py
    └── ir/
        └── test_base_script_item.py
```

## When to Split Test Files

Split a test file when:

1. **Conceptual separation** - Testing distinct sub-concepts
   ```
   test_graph.py → test_graph_topology.py + test_graph_hierarchy.py
   ```

2. **File becomes very large** - >1000 lines
   - But ensure split is logical, not arbitrary

3. **Different fixture requirements** - Tests need very different setup

**Never split for:**
- Arbitrary line count limits
- "Part 1" and "Part 2" divisions
- Running out of test names

## Adding New Tests

When adding a new test:

1. **Find the right file** - Does a test file exist for this concept?
2. **Find the right class** - Which aspect are you testing?
3. **Follow the pattern** - Use consistent structure and naming
4. **Keep it focused** - Test one thing clearly
5. **Add docstrings** - Especially for complex scenarios

## Refactoring Tests

When refactoring:

1. **Preserve all test coverage** - Don't lose tests
2. **Follow the organizational principles** - Concept-based grouping
3. **Eliminate true duplicates** - Not just similar tests
4. **Update documentation** - Keep README.md current
5. **Validate before removing** - Ensure new tests pass

## Examples

See these files for excellent examples:

- `tests/core/entity/test_entity_consolidated.py` - Comprehensive entity testing
- `tests/core/singleton/test_singleton_consolidated.py` - Singleton and inheritance
- `tests/core/test_content_addressable.py` - Focused module testing

These demonstrate:
- Clear organization into test classes
- Descriptive test names
- Comprehensive coverage
- Minimal duplication
- Good use of fixtures and helpers
- Progressive complexity
