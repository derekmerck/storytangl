# tangl.service — Design Notes

> Status: Current manager-first contract
> Authority: The canonical public service surface is `ServiceManager`,
> `build_service_manager`, `service_method`, auth helpers, and the typed
> response models in `response.py`.

## Position in the Architecture

Service is the boundary layer between applications and the engine nucleus.
Applications call service; service opens persistence-backed resources and calls
into story/vm/core. Nothing below service imports upward.

```
Applications → CLI, REST, future transports
Service      → Lifecycle, auth, persistence, typed operations
Story        → Narrative vocabulary, compilation, journal policy
VM           → Runtime execution, provisioning, traversal
Core         → Timeless graph/entity/dispatch primitives
```

## Canonical Surface

`ServiceManager` is the only canonical public service object.

- Public use cases are explicit methods such as `create_story`,
  `resolve_choice`, `get_story_update`, `get_user_info`, `get_world_info`, and
  `get_system_info`.
- `build_service_manager(...)` is the canonical bootstrap helper.
- `@service_method(...)` is bounded descriptive metadata on manager methods:
  access class, context class, writeback policy, blocking hint, optional
  capability tag, and optional operation id.
- Typed response models are the public payload contract:
  `RuntimeEnvelope`, `ProjectedState`, `RuntimeInfo`, `UserInfo`, `WorldInfo`,
  `SystemInfo`, and `UserSecret`.

The deleted orchestrator/controller/gateway/token stack is no longer part of
the service design. Any remaining transport glue should derive from
`ServiceManager` metadata and delegate directly to manager methods.

## Resource Model

Service manages four distinct runtime resources:

| Resource | Lifecycle | Identity | Managed by |
|----------|-----------|----------|------------|
| `User` | Persistent | UUID | `PersistenceManager` + `ServiceManager` |
| `Ledger` | Persistent | UUID | `PersistenceManager` + `ServiceManager` |
| `Frame` | Ephemeral | Derived from `Ledger` | `Ledger.get_frame()` |
| `World` | Loadable | Label | `WorldRegistry` |

`User` tracks caller identity and session affinity.

`Ledger` is the durable story/session state: graph, cursor, journal/replay
artifacts, and user linkage.

`Frame` is per-request execution context. Service does not persist frames.

`World` is discovered and compiled through `WorldRegistry`. Service owns world
loading/unloading policy, not world semantics.

## Execution Model

Service methods open the resources they need explicitly:

- `open_user(user_id, write_back=...)`
- `open_world(world_id)`
- `open_session(user_id=..., ledger_id=..., write_back=...)`

`open_session(...)` is the canonical session helper. It resolves the user,
derives or loads the ledger, creates a fresh frame, and handles writeback on
exit. This replaces the deleted generic resource-binding and path-based
writeback machinery.

Service methods are direct Python code, not metadata-driven endpoint
dispatchers. The metadata exists for wrappers, docs, and access checks; it does
not assemble or execute the service layer.

## Response Contract

The canonical response contract is typed Python models:

- Story session methods return `RuntimeEnvelope` directly.
- Informational reads return typed info models such as `ProjectedState`,
  `UserInfo`, `WorldInfo`, and `SystemInfo`.
- Mutation acknowledgements return `RuntimeInfo`.

Service does not own transport formatting. HTML transforms, media URL shaping,
and similar wire concerns belong in CLI/server adapters.

`RuntimeEnvelope.fragments` carries real fragment models. Service does not
maintain a second fragment representation.

## Auth and Access

`UserAuthInfo` is the service auth context. Auth resolution is persistence-based
and returns concrete user identity plus privilege state.

`service_method` access metadata is authoritative for wrappers/transports:

- `public` — callable without user auth
- `client` — normal authenticated client call
- `dev` — privileged/admin-only call

Writeback metadata is likewise authoritative for deciding whether a method
should persist user/session state on exit.

## World Support

`WorldRegistry` is the canonical world discovery/loading path.

- `ServiceManager.open_world(...)` resolves worlds through the registry or the
  explicitly registered in-process world map.
- `load_world`, `unload_world`, `get_world_media`, and `reset_system` remain
  available in this Python implementation as optional capabilities.
- Media delivery is implementation-specific service support, not part of the
  portable service nucleus.

## What Service Does Not Define

Service does not define:

- narrative entities, compilation, or journal policy
- traversal, provisioning, or phase execution
- graph/entity base types
- persistence backend implementations
- transport routing or serialization formats

Service is the lifecycle and contract layer over the engine, not a second
runtime.
