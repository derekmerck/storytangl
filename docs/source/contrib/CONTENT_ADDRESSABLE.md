# Content-Addressable Records

## Overview
ContentAddressable is a mixin for Record types that need content-based identity in addition to UID-based identity. It automatically computes a `content_hash` from the record's content, enabling deduplication, provenance tracking, and content-based lookups.

## When to Use

Use ContentAddressable when your Record type needs:

1. **Deduplication** - Same content should be recognized as identical
2. **Provenance** - Track exactly what content was used
3. **Content Lookups** - Find records by their content, not just UID
4. **Immutability Verification** - Detect if content changes

## Usage

### Basic Usage (Default Hashing)

```python
from tangl.core.entity import Record
from tangl.core.content_addressable import ContentAddressable

class MyTemplate(Record, ContentAddressable):
    name: str
    archetype: str
    hp: int
    # content_hash auto-computed from all fields except uid
```

### Custom Hashing

```python
class MyResource(Record, ContentAddressable):
    path: Path
    metadata: dict
    
    @classmethod
    def _get_hashable_content(cls, data: dict):
        # Only hash the file content, not metadata
        if 'path' in data:
            from tangl.utils.hashing import compute_data_hash
            return compute_data_hash(Path(data['path']))
        return None
```

### Accessing the Hash

```python
template = MyTemplate(name="guard", archetype="soldier", hp=50)

# Full hash (bytes)
full_hash: bytes = template.content_hash

# Truncated hex (for display/logging)
short_id: str = template.get_content_identifier()  # First 16 hex chars
```

## How It Works

### Automatic Computation

1. When you construct a Record with ContentAddressable:
   ```python
   record = MyRecord(field1="value", field2=42)
   ```

2. The `@model_validator` calls `_get_hashable_content(data)`

3. Result is passed to `hashing_func()` (from tangl.utils.hashing)

4. Computed hash is set as `content_hash` field

### Default Behavior

By default, ContentAddressable hashes the entire record **except**:
- `uid` (instance-specific)
- `content_hash` (would be circular)
- `created_at`, `updated_at` (temporal metadata)

### Customization

Override `_get_hashable_content()` to:
- Exclude additional fields (like `scope`, `label` for templates)
- Include only specific fields
- Hash external content (file data, URLs)
- Skip hashing entirely (return None)

## Examples

### Template Hashing

```python
class ActorScript(Record, ContentAddressable):
    name: str
    archetype: str
    hp: int
    scope: ScopeSelector = None  # Metadata, don't hash
    label: str = None  # Metadata, don't hash
    
    @classmethod
    def _get_hashable_content(cls, data: dict):
        # Hash structure, not metadata
        exclude = {'uid', 'content_hash', 'scope', 'label'}
        return {k: v for k, v in data.items() if k not in exclude}
```

**Result:** Templates with same `name`, `archetype`, `hp` get same hash, regardless of `scope` or `label`.

### Media Resource Hashing

```python
class MediaRIT(Entity, ContentAddressable):
    path: Path = None
    data: bytes = None
    
    @classmethod
    def _get_hashable_content(cls, data: dict):
        # Hash actual file/data content
        if 'data' in data:
            return data['data']
        elif 'path' in data:
            return compute_data_hash(Path(data['path']))
        raise ValueError("Must provide data or path")
```

**Result:** Files with same content get same hash, even if paths differ.

## Integration with Registry

Because `content_hash` is marked as an identifier (`is_identifier=True`), Registry can find records by hash:

```python
# Add templates to registry
template1 = ActorScript(name="guard", hp=50)
template2 = ActorScript(name="guard", hp=50)  # Same content
registry.add(template1)
registry.add(template2)  # Duplicate - same hash

# Find by content hash
matches = registry.find_all(content_hash=template1.content_hash)
assert len(matches) == 2  # Both instances
assert matches[0].content_hash == matches[1].content_hash
```

## Provenance Tracking

Use `content_hash` in BuildReceipts to track what was used:

```python
# In provisioner
template = world.template_registry.find_one(label="guard")

receipt = BuildReceipt(
    destination_uid=actor.uid,
    metadata={
        'template_ref': 'guard',
        'template_hash': template.get_content_identifier(),
        # Can verify later that exact template was used
    }
)
```

## Best Practices

### DO:
- ✅ Use for immutable content (templates, resources)
- ✅ Exclude metadata from hash (scope, labels, timestamps)
- ✅ Document what fields are hashed in `_get_hashable_content()`
- ✅ Use `get_content_identifier()` for logging

### DON'T:
- ❌ Use for frequently-mutating records (defeats caching)
- ❌ Hash sensitive data without considering privacy
- ❌ Assume hash uniqueness (collisions theoretically possible)
- ❌ Use hash as primary key (UID is primary, hash is alias)

## Performance Notes

- Hash computation happens once at construction
- Records are frozen (immutable), so hash never changes
- No caching needed (computed once, stored forever)
- `hashing_func()` is fast (Blake2b or SHA224)

## Troubleshooting

**"Hash not computed"**
- `_get_hashable_content()` returned None
- Check your override implementation

**"Same content, different hashes"**
- Metadata fields being included in hash
- Add them to exclude set in `_get_hashable_content()`

**"Different content, same hash" (collision)**
- Astronomically unlikely with Blake2b/SHA224
- Report as bug if confirmed

## See Also

- MediaResourceInventoryTag - Example using ContentAddressable
- BaseScriptItem - Templates using ContentAddressable
- Registry - Content-based lookups
