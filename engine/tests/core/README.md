# Core Package Test Suite

This directory contains tests for the `tangl.core` package, organized around key architectural concepts.

## Test Organization

Tests are organized by the core concept being tested, not by implementation details. Each test file corresponds to a major concept in the core package.

### Current Test Structure

```
tests/core/
├── entity/
│   └── test_entity_consolidated.py    # Entity: identity, matching, tags, serialization
├── singleton/
│   └── test_singleton_consolidated.py # Singleton & InheritingSingleton
├── registry/
│   └── test_registry.py               # Registry: CRUD, search, filtering
├── graph/
│   ├── test_graph.py                  # Graph, Node, Edge basics
│   ├── test_node.py                   # Node-specific functionality
│   ├── test_edge.py                   # Edge-specific functionality
│   └── test_token.py                  # Token specialization
├── factory/
│   ├── test_templates.py              # Template system
│   └── test_token_factory.py          # Token factory
├── dispatch/
│   ├── test_dispatch_comprehensive.py # Core dispatch system
│   └── test_handlers.py               # Dispatch handlers
├── test_content_addressable.py        # ContentAddressable
├── test_record_stream.py              # Record & StreamRegistry
└── test_structuring.py                # Serialization utilities
```

## Test File Pattern

Each test file follows a consistent structure:

```python
"""Tests for [module/concept]

Organized by functionality:
- [Feature 1]
- [Feature 2]
- [Feature 3]
"""

# ============================================================================
# Test Fixtures and Helper Classes
# ============================================================================

# Shared fixtures, helper classes, and test data

# ============================================================================
# [Feature 1]
# ============================================================================

class Test[Feature1]:
    """Tests for [feature 1 description]."""

    def test_basic_behavior(self):
        """Test the basic/happy path."""
        pass

    def test_edge_case(self):
        """Test edge cases and boundaries."""
        pass

    def test_error_handling(self):
        """Test error conditions."""
        pass

# ============================================================================
# [Feature 2]
# ============================================================================

class Test[Feature2]:
    """Tests for [feature 2 description]."""
    pass
```

## Writing Tests

### Test Naming Conventions

1. **Test functions:** `test_<what>_<condition>`
   - Good: `test_entity_matches_by_label_and_tags`
   - Bad: `test_matches_1`

2. **Test classes:** `Test<Concept><Aspect>`
   - Good: `TestEntitySerialization`
   - Bad: `TestEntityStuff`

3. **Helper classes:** `<Concept>` (no "Test" prefix)
   - Good: `Person(Entity):`
   - Bad: `TestPerson(Entity):`

### Test Organization

Group tests into classes by **functionality**, not by implementation:

```python
# Good: Organized by what the tests do
class TestEntityMatching:
    """Tests for entity.matches() functionality."""

class TestEntitySerialization:
    """Tests for unstructure/structure roundtrip."""

# Bad: Organized by arbitrary grouping
class TestEntity1:
    """First batch of entity tests."""

class TestEntity2:
    """More entity tests."""
```

### Test Clarity

1. **One concept per test**
   ```python
   # Good: Tests one specific behavior
   def test_entity_matches_by_label(self):
       e = Entity(label="hero")
       assert e.matches(label="hero")

   # Bad: Tests multiple unrelated things
   def test_entity_stuff(self):
       e = Entity(label="hero")
       assert e.matches(label="hero")
       assert e.get_label() == "hero"
       assert len(e.tags) == 0
   ```

2. **Descriptive assertions**
   ```python
   # Good: Clear failure message
   assert child.value == 20, "Child should override parent value"

   # Acceptable: Assertion is obvious
   assert child.value == 20
   ```

3. **Minimal setup**
   ```python
   # Good: Only create what you need
   def test_entity_label(self):
       e = Entity(label="test")
       assert e.label == "test"

   # Bad: Unnecessary complexity
   def test_entity_label(self):
       e1 = Entity(label="test1", tags={"a", "b"})
       e2 = Entity(label="test2", tags={"c", "d"})
       reg = Registry()
       reg.add(e1)
       reg.add(e2)
       assert e1.label == "test1"
   ```

### Fixtures and Helpers

1. **Use fixtures for shared setup**
   ```python
   @pytest.fixture
   def sample_entity():
       return Entity(label="test", tags={"a", "b"})

   def test_entity_tags(sample_entity):
       assert sample_entity.has_tags("a")
   ```

2. **Use helper classes for test entities**
   ```python
   # At the top of the file
   class Person(Entity):
       """Test entity with person attributes."""
       name: str
       age: int

   # In tests
   def test_person_matching():
       p = Person(name="Alice", age=30)
       assert p.matches(name="Alice")
   ```

3. **Clean up after tests**
   ```python
   @pytest.fixture(autouse=True)
   def clear_singletons():
       Singleton.clear_instances()
       yield
       Singleton.clear_instances()
   ```

## Running Tests

### Run all core tests
```bash
pytest tests/core/
```

### Run tests for specific concept
```bash
pytest tests/core/entity/
pytest tests/core/singleton/
```

### Run specific test class
```bash
pytest tests/core/entity/test_entity_consolidated.py::TestEntityMatching
```

### Run specific test
```bash
pytest tests/core/entity/test_entity_consolidated.py::TestEntityMatching::test_matches_by_label
```

### Run with coverage
```bash
pytest tests/core/ --cov=src/tangl/core --cov-report=term-missing
```

## Coverage Goals

Each test file should comprehensively test its concept:

- ✅ **Basic functionality** - Happy path tests
- ✅ **Edge cases** - Boundary conditions, empty inputs, None values
- ✅ **Error handling** - Invalid inputs, exceptions
- ✅ **Serialization** - Roundtrip testing for persistent objects
- ✅ **Integration** - How the concept works with related concepts

## Adding New Tests

When adding tests:

1. **Find the right file**
   - Does a test file exist for this concept?
   - If not, create one following the pattern

2. **Find the right class**
   - Which aspect of the concept are you testing?
   - Add to existing class or create new one

3. **Follow the pattern**
   - Use descriptive names
   - Keep tests focused
   - Add docstrings for complex tests

4. **Don't create numbered files**
   - No `test_foo_2.py`
   - Add to existing file or refactor into logical groups

## Refactoring Tests

If a test file becomes too large (>1000 lines):

1. **Consider splitting by sub-concept**
   - Example: `test_graph.py` → `test_graph_topology.py` + `test_graph_hierarchy.py`

2. **Not by arbitrary grouping**
   - Bad: `test_graph_1.py`, `test_graph_2.py`

3. **Document the split**
   - Update this README
   - Add docstrings explaining organization

## Examples

See the consolidated test files for examples of good test organization:

- `entity/test_entity_consolidated.py` - Comprehensive entity testing
- `singleton/test_singleton_consolidated.py` - Singleton and inheritance testing

These files demonstrate:
- Clear organization into test classes
- Descriptive test names
- Comprehensive coverage
- Minimal duplication
- Good use of fixtures and helpers
