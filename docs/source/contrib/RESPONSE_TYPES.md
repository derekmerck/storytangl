# Response Type Decision Matrix

## ResponseType.CONTENT

**Use when:** Endpoint returns narrative content fragments from the journal.

**Return type:** `list[BaseFragment]` (FragmentStream alias)

**Examples:**
- `get_journal_entries()` - returns last N fragments
- `get_story_update()` - returns blocks + choices + media

**Characteristics:**
- Read-only (MethodType.READ)
- Returns story discourse (what player sees)
- Ordered, sequential output

---

## ResponseType.INFO

**Use when:** Endpoint queries metadata without side effects.

**Return type:** Subclass of `InfoModel` (UserInfo, StoryInfo, WorldInfo, SystemInfo)

**Examples:**
- `get_story_info()` - ledger metadata (title, step, cursor)
- `get_user_info()` - account details, achievements
- `list_worlds()` - available world templates

**Characteristics:**
- Read-only (MethodType.READ)
- Returns structured metadata (not narrative)
- Idempotent queries

---

## ResponseType.RUNTIME

**Use when:** Endpoint performs state mutation or control operation.

**Return type:** `RuntimeInfo`

**Examples:**
- `resolve_choice()` - player took action
- `create_story()` - new ledger created
- `drop_story()` - ledger deleted
- `jump_to_node()` - cursor moved

**Characteristics:**
- Write operations (CREATE/UPDATE/DELETE)
- Returns acknowledgment + cursor position
- May succeed (status="ok") or fail (status="error")

**RuntimeInfo fields:**
- `status`: "ok" | "error"
- `code`: Optional error code (e.g., "CHOICE_NOT_FOUND")
- `message`: Human-readable description
- `cursor_id`, `step`: Current position (if applicable)
- `details`: Free-form metadata (controller-specific data)

---

## ResponseType.MEDIA

**Use when:** Endpoint returns binary/media content.

**Return type:** `MediaFragment` (at native layer)

**Examples:**
- `get_asset()` - retrieve image/audio file
- `get_world_cover()` - world banner image

**Characteristics:**
- Read-only (MethodType.READ)
- Returns media objects with RITs (not HTTP URLs yet)
- Service layer dereferences RIT → backend-specific format
- Transport layer converts to URL/base64/file path

**Status:** Media endpoints not yet implemented in MVP.

---

## Decision Flowchart

```
Does endpoint return narrative fragments?
  YES → CONTENT
  NO ↓

Does endpoint mutate state?
  YES → RUNTIME
  NO ↓

Does endpoint return media/assets?
  YES → MEDIA
  NO ↓

Endpoint returns metadata
  → INFO
```
