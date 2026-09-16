# tangl.service — Design Notes

> Status: Current manager-first contract
> Authority: The canonical public service surface is `ServiceManager`,
> `RemoteServiceManager`, `build_service_manager`, `service_method`, auth
> helpers, and the typed response models in `response.py`.

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
- `RemoteServiceManager` is an optional transport-backed implementation that
  fulfills the same public manager contract through the REST API for the subset
  of methods with route parity.
- `@service_method(...)` is bounded descriptive metadata on manager methods:
  access class, context class, writeback policy, blocking hint, optional
  capability tag, and optional operation id.
- Typed service responses and presentation payloads are the public contract:
  `RuntimeEnvelope`, `RuntimeInfo`, `UserInfo`, `WorldInfo`, `SystemInfo`,
  `UserSecret`, and presentation-owned `ProjectedState`.

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

Remote mode is still service-first. It does not expose remote persistence,
session hydration, or resource-opening helpers. In current v1 relay mode,
protected upstream calls execute under one configured upstream identity rather
than forwarding each caller's auth context end-to-end.

### Deferred trusted live-debug interface

The reference service retains the design for a privileged live-story console,
tracked for reconnection in issue #478. It is intended for interactive world
review and support, especially when a large story is easier to investigate from
inside a running ledger than by reconstructing its state from authored inputs.
The existing cmd2 `inspect`, `check`, `apply`, and `goto_node` commands and the
restricted REST routes are currently stubs; this section records their intended
contract, not an available public capability.

Debug operations use the ordinary manager/session lifecycle. They open the
ledger through `ServiceManager`, construct its real phase context and namespace,
record any causality transition before potentially mutating work, checkpoint
and persist through the normal writeback path, and return the ordinary typed
response. They do not reach around the manager to mutate a graph dictionary.

Ledger causality is a reproducibility receipt, not anti-cheat policy:

- `clean` means the state and cursor derive from the world revision and recorded
  reader choices under deterministic runtime inputs;
- `soft_dirty` means trusted evaluation or state mutation occurred while the
  current topology remains structurally credible, so normal availability and
  provisioning still apply;
- `hard_dirty` means reachability or topology was deliberately broken, such as
  teleporting into a locked room. Availability relaxation and stub provisioning
  then favor a playable exploratory frontier over preserving constraints whose
  prerequisites were bypassed.

The mode is monotonic within one ledger. A clean causal claim requires branching
or restarting from a clean checkpoint; clearing a flag cannot reconstruct the
missing cause. Dirty ledgers remain playable and persistable, but replay after
the transition may rely on stored checkpoints/deltas rather than claiming that
the original choice sequence produced the state.

`inspect` is a bounded structured read. `check` evaluates a Python expression
against the active namespace and marks soft dirty before evaluation because an
apparently read-only expression can call a mutating method. `apply` executes an
`Effect` and normally marks soft dirty. Cursor jumps, forced unavailable
traversal, accepted unresolved stubs, and explicitly structural mutations
escalate hard dirty before crossing the authored causal frontier.

The direct manager-backed CLI is the primary intended adapter. Optional
transport exposure uses two independent gates. The hosting application must
explicitly enable its restricted/development surface (disabled by default), and
the gateway must resolve the request's API key to a user whose account has the
privilege flag before invoking a method marked `ServiceAccess.DEV`. Enabling
development mode does not promote ordinary users, and possessing a privileged
account does not make a production server expose routes it declined to mount or
enable.

The authorization groups are public, user, and admin. Public operations require
no API key and include resources such as world information, media when exposed
by the adapter, and the web client. Current v1 remote coverage does not expose
world media. User operations require a valid unprivileged API key. Admin
operations require a valid API key whose user has the privilege flag. These
groups currently map to the `PUBLIC`, `CLIENT`, and `DEV` service access markers
respectively; the marker names describe service exposure, not separate kinds of
story player. The direct CLI should likewise make trusted debug mode explicit
rather than infer admin privilege merely from being local. Remote parity is not
required.

Restricted builtins are not a security sandbox when the namespace contains live
Python objects. The Python expression capability is deliberate for the
reference-engine developer console and does not require a speculative
cross-language expression replacement.

### Remote Setup (v1)

Remote mode is selected through `build_service_manager(...)` or config:

```toml
[service.manager]
backend = "remote"

[service.remote]
api_url = "http://127.0.0.1:8000/api/v2"
api_key = ""
secret = ""
timeout_s = 5.0
```

Typical CLI usage in v1 is:

1. point the manager at a remote REST server with `service.manager.backend = "remote"`
2. leave `api_key`/`secret` blank for anonymous bootstrap
3. create a user through the service surface
4. play stories normally through the same manager methods

The remote manager is a transport adapter, not a second persistence model. The
server still owns worlds, users, ledgers, and session state.

### Remote Coverage (v1)

Supported through REST parity today:

- `create_story`
- `resolve_choice`
- `get_story_update`
- `get_story_info`
- `drop_story`
- `create_user`
- `update_user` for secret rotation only
- `get_user_info`
- `drop_user`
- `get_key_for_secret`
- `list_worlds`
- `get_world_info`
- `get_system_info`

Explicitly unsupported in current remote mode:

- local resource-opening helpers such as `open_user`, `open_ledger`,
  `open_session`, and `open_world`
- world media access
- world mutation (`load_world`, `unload_world`)
- dev/system mutation (`reset_system`)

## Response Contract

The canonical response contract is typed Python models:

- Story session methods return `RuntimeEnvelope` directly.
- Informational reads return typed payloads such as presentation-owned
  `ProjectedState`, `UserInfo`, `WorldInfo`, and `SystemInfo`.
- Mutation acknowledgements return `RuntimeInfo`.

Service does not own transport formatting. HTML transforms, media URL shaping,
and similar wire concerns belong in CLI/server adapters.

`RuntimeEnvelope.fragments` carries real fragment models. Service does not
translate journal content into a second shape or maintain a second fragment
representation.

## Info Channels

`get_story_info` is the generic side-channel for supplementary projected state.
It returns presentation-owned `ProjectedState`, the same portable section model
used by status rails, command-line inspection, and future rich panels. With no
`channels` query it returns the exact channels valid for the authenticated
story. `channels=a,b` selects only those channels, deduplicated in request order;
an unknown id is a bad request.

`get_world_info` uses the same protocol for public, fixed, cacheable world
projections. It is available without a story session and currently advertises
common HTML class meanings plus advisory branding, light/dark tokens, and a
logo media reference. These are suggestions a client may ignore or adjust.

Service folds the presentation registry with story, world, and runtime-local
authorities:

- `advertise_story_info_channels` gathers exact story channel ids, while
  `advertise_world_info_channels` gathers only public world-static channel ids.
- `get_story_info` and `get_world_info` gather `ProjectedSection` values for a
  concrete `ProjectionRequest`.

Service owns the exact `ui-sidebar` story channel and its minimal session
projection. Runtime envelopes carry only `InfoState` version, dirty, and
availability hints; the full catalog is discovered through the info endpoint.

One exact channel may contribute several sections. Service dispatches selected
channels one at a time to preserve request order. There is no glob expansion,
folder hierarchy, provider recruitment, or specificity ranking. Handlers treat
projected state as disclosed state, not authority state: a sandbox map may show
known rooms and visible exits, but not hidden truth or future schedules.

Any hotspot, edge reference, or action hint carried in a projected section is
advisory. Committing a move still goes through ordinary action selection.

## Auth and Access

`UserAuthInfo` is the service auth context. Auth resolution is persistence-based
and returns concrete user identity plus privilege state.

`service_method` access metadata is authoritative for wrappers/transports:

- `public` — callable without user auth
- `client` — normal authenticated client call
- `dev` — privileged/admin-only call

Writeback metadata is likewise authoritative for deciding whether a method
should persist user/session state on exit.

### Browser player-session bootstrap

The web client owns a deliberately small, codename-backed persistence
capability: the server stores a derived secret hash and stable user UUID, while
the browser retains the plaintext codename needed to restore that user. The
derived API key is request transport, not a second identity. See the canonical
[player-session bootstrap note](../../../../apps/web/notes/PLAYER_SESSION_BOOTSTRAP.md)
for create-or-restore, rotation, and explicitly deferred security policy.

## World Support

`WorldRegistry` is the canonical world discovery/loading path.

- `ServiceManager.open_world(...)` resolves worlds through the registry or the
  explicitly registered in-process world map.
- `load_world`, `unload_world`, `get_world_media`, and `reset_system` remain
  available in this Python implementation as optional capabilities.
- Media delivery is implementation-specific service support, not part of the
  portable service nucleus.

World domain code is the authored composition root. It selects top-level
mechanics and provides domain policy, catalogs, templates, resources, and
special handlers. Service discovers and opens the resulting world; it neither
imports those mechanics nor reconstructs their policy at the transport layer.

## What Service Does Not Define

Service does not define:

- narrative entities, compilation, or journal policy
- traversal, provisioning, or phase execution
- graph/entity base types
- persistence backend implementations
- transport routing or serialization formats
- mechanic selection or world-domain policy

Service is the lifecycle and contract layer over the engine, not a second
runtime.
