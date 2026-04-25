# Response Type Decision Matrix

## ResponseType.CONTENT

**Use when:** Internal code needs a plain narrative fragment stream without
runtime cursor metadata.

**Return type:** `list[BaseFragment]` (FragmentStream alias)

**Examples:**
- lower-level journal reads that return last N fragments
- test helpers or adapters that intentionally do not need a runtime envelope

**Characteristics:**
- Read-only (MethodType.READ)
- Returns story discourse without session status
- Ordered, sequential output

**Status:** Internal/narrow. Public story-session service methods return
`RuntimeEnvelope` rather than raw fragment lists.

---

## ResponseType.RUNTIME_ENVELOPE

**Use when:** Endpoint returns ordered story fragments plus cursor/session
metadata.

**Return type:** `RuntimeEnvelope`

**Examples:**
- `create_story()` - creates a ledger and returns the initial envelope
- `resolve_choice()` - advances the story and returns new fragments
- `get_story_update()` - returns ordered runtime fragments for the active story

**Characteristics:**
- Carries `cursor_id`, `step`, redirect metadata, and service metadata
- Carries `fragments: list[BaseFragment]`
- The client renders fragments directly through a registry/shell model
- Unknown fragment types are valid extension points and must survive transport

See `FRAGMENT_STREAM_CONTRACT.md` for the detailed client-facing contract.

---

## ResponseType.INFO

**Use when:** Endpoint queries metadata without side effects.

**Return type:** Subclass of `InfoModel` (ProjectedState, UserInfo, WorldInfo, SystemInfo)

**Examples:**
- `get_story_info()` - projected current-state sections
- `get_user_info()` - account details, achievements
- `list_worlds()` - available world templates

**Characteristics:**
- Read-only (MethodType.READ)
- Returns structured metadata (not narrative)
- Idempotent queries

---

## ResponseType.RUNTIME

**Use when:** Endpoint returns a runtime/status envelope rather than plain
metadata or narrative fragments. This is for acknowledgement/control operations
that do not return a story fragment batch.

**Return type:** `RuntimeInfo`

**Examples:**
- `drop_story()` - ledger deleted
- future maintenance or control operations that need status/details only

**Characteristics:**
- Common for write operations, but not limited to them
- Returns acknowledgment and optional cursor position
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
- `get_world_media()` - retrieve world-scoped media payloads
- future asset/media fetch endpoints with native media payloads

**Characteristics:**
- Read-only (MethodType.READ)
- Returns media objects with RITs (not HTTP URLs yet)
- Service layer dereferences RIT → backend-specific format
- Transport layer converts to URL/base64/file path

**Status:** Active. Current service surfaces already include world-media
responses, and gateway/transport layers may further adapt those payloads.

---

## Decision Flowchart

```
Does endpoint return narrative fragments?
  YES → RUNTIME_ENVELOPE for public story sessions
        CONTENT only for lower-level raw-fragment helpers
  NO ↓

Does endpoint mutate state?
  YES → RUNTIME_ENVELOPE if it advances story and returns fragments
        RUNTIME if it is acknowledgement/status only
  NO ↓

Does endpoint return media/assets?
  YES → MEDIA
  NO ↓

Endpoint returns metadata
  → INFO
```
