# tangl.service — Design Notes

> Status: Current contract
> Authority: The service-native response contract lives in `engine/src/tangl/service/response.py`; projected runtime state is defined there as `ProjectedState`.

> Architectural intent, design decisions, and rationale for the canonical service
> package of the StoryTangl narrative engine.
> This document describes the current v3.8 framework. The source packages are
> `tangl.core`, `tangl.vm`, `tangl.story`, and `tangl.service` (no version suffix).

---

## Position in the Architecture

Service is the boundary layer. It is the **only** interface between applications
and the engine. Applications (CLI, REST, future GraphQL) call into service;
service calls into story, vm, and core. The engine layers below service never
import from it.

```
Applications → tangl.cli, tangl.rest, future transports
Service      → Orchestration, lifecycle, auth, response shaping  ← this document
Story        → Domain semantics, narrative concepts
VM           → Temporal evolution, context-dependent evaluation
Core         → Timeless primitives and mechanisms
```

### Litmus Test

| Question                                                   | Layer      |
|------------------------------------------------------------|------------|
| Does it manage how an application invokes the engine?      | Service    |
| Does it hydrate, cache, or persist engine resources?       | Service    |
| Does it define the response vocabulary for transports?     | Service    |
| Does it define narrative entities or compilation?          | Story      |
| Does it define traversal or provisioning mechanics?        | VM         |

### Service's Defining Characteristic

Service defines the canonical invocation contract for the engine: how callers
identify operations, how execution context is hydrated, how mutations are
persisted, and how results are classified for transport. The orchestrator handles
resource hydration, access, and writeback; controllers express application use
cases in engine terms; the gateway stabilizes and transforms the external API
surface.

### Current Service Semantics

Five statements that orient readers quickly:

- Applications invoke **stable operation tokens** through the gateway or
  **internal endpoint names** through the orchestrator. They never construct
  engine objects or call story/vm layers directly.
- The orchestrator **hydrates resources** (`User`, `Ledger`, `Frame`) from type
  hints on controller method signatures and handles persistence writeback
  according to endpoint policy.
- **Controllers** are small service façades over engine use cases. They call
  story/vm APIs and return native results; they know nothing about transport,
  persistence, or serialization.
- The **gateway** adds a stable operation-token API, inbound parameter
  normalization, and outbound response transformation (render profiles) on top
  of the orchestrator.
- **Response types** classify what an endpoint produces (content, info, runtime,
  media), which determines how the result is validated, normalized, and
  serialized by transport.

### What Service Explicitly Does NOT Define

- Narrative entity types, compilation, or journal rendering (Story)
- World/domain semantics beyond lifecycle and discovery (Story/World facets)
- Traversal mechanics, provisioning, or the phase pipeline (VM)
- Graph topology, registries, or entity base classes (Core)
- Transport-specific routing, middleware, or wire formats (Applications)
- Persistence backend implementations (`tangl.persistence`)

Service *coordinates* persistence but does not implement storage backends.
It *defines* the response vocabulary but does not format wire payloads; that is
the transport layer's job.

---

## Service Module Map

```
tangl.service
├── Gateway tier
│   → gateway.py           (ServiceGateway: operation-token execution with hooks)
│   → rest_adapter.py      (GatewayRestAdapter: transport normalization)
│   → hooks.py             (GatewayHooks: inbound/outbound behavior pipelines)
│   → operations.py        (ServiceOperation enum, token ↔ endpoint mapping)
│   → bootstrap.py         (build_service_gateway: assembly-time wiring)
├── Orchestrator tier
│   → orchestrator.py      (Orchestrator: binding, hydration, invocation, writeback)
│   → api_endpoint.py      (ApiEndpoint decorator, policy types, enums)
├── Controllers
│   → controllers/runtime_controller.py  (story session lifecycle)
│   → controllers/world_controller.py    (world catalog and loading)
│   → controllers/system_controller.py   (health and diagnostics)
│   → user/user_controller.py            (user CRUD and auth)
├── Response and auth
│   → response.py          (RuntimeInfo, RuntimeEnvelope, InfoModel, domain info models)
│   → exceptions.py        (ServiceError hierarchy → RuntimeInfo error codes)
│   → auth.py              (UserAuthInfo, API key resolution)
└── Domain support
    → user/user.py         (User entity model)
    → media.py             (media fragment → service-facing payload translation)
    → world_registry.py    (world discovery and lazy compilation)
```

---

## Service Resource Model

Service turns engine-adjacent objects into addressable runtime resources with
distinct lifecycle semantics. Understanding these four resources and their
lifecycles is prerequisite to understanding the orchestrator:

| Resource | Lifecycle     | Identity            | Managed by         |
|----------|---------------|---------------------|--------------------|
| **User** | Persistent    | UUID + content_hash | Orchestrator + persistence |
| **Ledger** | Persistent  | UUID, linked to user via `current_ledger_id` | Orchestrator + persistence |
| **Frame** | Ephemeral    | Derived from Ledger per request | Orchestrator (not persisted) |
| **World** | Loadable     | Label in process-local registry | WorldRegistry |

**User** provides caller identity and session affinity. It tracks which ledger
the user is currently playing. User is service-owned; story and vm don't know
about users.

**Ledger** provides durable story/session state: graph, cursor, step count,
replay artifacts. It is the persistence unit for a story instance.

**Frame** provides ephemeral execution context derived from a Ledger. The
orchestrator creates one fresh Frame per request via `ledger.get_frame()` and
discards it after execution. Frames are never persisted. This is a deliberate
design choice: the application asks for a session update, and the engine gets a
fresh execution context derived from durable state. No stale frames, no
concurrency hazards from cached execution contexts.

**World** provides discoverable, loadable authored content. Worlds are compiled
lazily by `WorldRegistry` and held in a process-local instance registry.
Service manages world lifecycle (discovery, loading, unloading); story defines
what a world *is*.

---

## Component Design

### The Three-Tier Execution Stack

Service has three tiers that progressively translate between application concerns
and engine execution. Each tier adds exactly one concern:

```
Transport (apps/cli, apps/server)
    ↓ operation token + params + render profile
ServiceGateway          ← external consumer contract + adaptation
    ↓ endpoint name + params (normalized)
Orchestrator            ← internal execution semantics + lifecycle
    ↓ hydrated resources + domain params
Controller method       ← use-case façade over engine APIs
    ↓ raw engine result
Orchestrator (writeback, cleanup)
    ↑ NativeResponse
ServiceGateway (outbound hooks)
    ↑ transformed result
Transport (serialization)
```

The **orchestrator** owns internal execution semantics: resource hydration,
access enforcement, invocation, writeback. The **gateway** owns the stable
external consumer contract: operation tokens, render profiles, inbound/outbound
hooks. This is not just layering; it separates concerns that evolve at different
rates. Internal orchestrator mechanics can change without affecting the operation
token API that external consumers depend on.


### Orchestrator (`orchestrator.py`)

The execution coordinator. Takes an endpoint name, figures out what resources the
controller needs, loads them, calls the controller, validates the result, and
persists mutated resources.

**Execution stages.** After Wave 1 decomposition, `execute()` is a thin
coordinator over five explicit stages:

1. **Binding resolution** — look up the endpoint name, get the controller and
   metadata
2. **Policy resolution** — merge endpoint defaults with per-call overrides
   (`ExecuteOptions`)
3. **Preparation** — hydrate resources from persistence based on type hints,
   enforce access control
4. **Invocation** — call the controller method, normalize and validate the
   result
5. **Finalization** — write back dirty resources, persist from explicit paths

**Resource hydration from type hints.** Controller methods declare what they need
via standard Python type hints: `user: User`, `ledger: Ledger`, `frame: Frame`.
The orchestrator inspects the signature, resolves `ResourceBinding` types, and
hydrates each resource from persistence or cache.

**The hydration cascade.** Resources have a deterministic resolution order:

- **User** — loaded from persistence by `user_id` (provided by transport)
- **Ledger** — loaded by explicit `ledger_id` parameter, or falling back to
  `user.current_ledger_id`
- **Frame** — ephemeral, created from the already-hydrated Ledger via
  `ledger.get_frame()`. Never persisted.

A controller can declare `(self, ledger: Ledger, frame: Frame, choice_id: UUID)`
and receive everything pre-resolved. The orchestrator handles the loading chain.

**Per-request cache.** Resources are cached by identity for the duration of one
`execute()` call. If both a Ledger-typed and a Frame-typed parameter need the
same ledger, it is loaded once. The cache is cleared between requests.

**Writeback is policy-driven.** `EndpointPolicy` controls cached-resource
writeback after execution. `WritebackMode.AUTO` uses method type to decide:
CREATE/UPDATE/DELETE endpoints write back, READ endpoints do not.
`WritebackMode.ALWAYS` forces cached writeback even for reads.
`WritebackMode.NEVER` suppresses cached writeback entirely.
`persist_paths` are orthogonal: they persist explicit resources reachable from
the result payload (for example `details.ledger` from `create_story`) regardless
of whether cached-resource writeback ran.

**Access enforcement.** `_enforce_access` checks the endpoint's `AccessLevel`
against the caller's resolved `UserAuthInfo`. `PUBLIC` endpoints skip the check.
`USER` endpoints require a resolved user matching the request's `user_id`.
`RESTRICTED` endpoints require the user to be privileged.


### ApiEndpoint (`api_endpoint.py`)

The metadata decorator that annotates controller methods with execution policy.

**`@ApiEndpoint.annotate()`** captures:

- `access_level` — PUBLIC, USER, or RESTRICTED
- `method_type` — READ, CREATE, UPDATE, or DELETE (inferred from method name
  when omitted)
- `response_type` — CONTENT, INFO, RUNTIME, or MEDIA
- `binds` — explicit tuple of `ResourceBinding` values (inferred from type hints
  when omitted)
- Preprocessor and postprocessor callables (hooks for parameter/result
  transformation)

**`method_type`** classifies mutation intent. Today it drives writeback decisions
(`AUTO` writes back mutating endpoints, not reads) and HTTP verb mapping in
transport layers. It establishes a policy hook for future auditing, routing, and
access-level semantics.

**`HasApiEndpoints`** is the mixin that controllers inherit. `get_api_endpoints()`
discovers all annotated methods and returns them as a name → endpoint mapping for
orchestrator registration.

**`EndpointPolicy`** separates execution behavior from endpoint identity.
Writeback mode, explicit persist paths, and future per-endpoint overrides live on
the policy, not on the endpoint. `bootstrap.py` applies default policy overrides
for endpoints that need them (for example `create_story` persists the created
ledger through an explicit `persist_paths` entry).


### ServiceGateway (`gateway.py`)

The external-facing execution surface built on top of the orchestrator.

**Operation tokens.** `ServiceGateway.execute(operation, ...)` accepts a
`ServiceOperation` enum value instead of a raw endpoint name. Operation tokens
are the stable external API; transports and clients reference tokens, not
controller method names. See *Two Names for One Endpoint* below.

**`execute_endpoint()`** is the escape hatch for controllers registered without
operation tokens (custom controllers, experimental endpoints). It resolves the
operation mapping if possible, and falls through to raw orchestrator execution
with endpoint-scoped hooks if not.

**Inbound/outbound hooks.** Every gateway execution passes through the
`GatewayHooks` pipeline:

- **Inbound hooks** normalize parameters before orchestrator execution (for
  example canonicalize `init_mode` string values for `create_story`)
- **Outbound hooks** transform results after execution based on the request's
  render profile (for example convert markdown to HTML, resolve media payloads
  to URLs, strip media for ASCII CLI output)

Hooks are registered with phase and priority, using the same `BehaviorRegistry`
mechanics from core. This makes the transformation pipeline composable and
auditable.

**Render profiles** are a `+`- or comma-separated token set (or an iterable of
tokens) that outbound hooks match against. `"raw"` means no transformation.
`"html"` triggers markdown rendering. `"media_url"` triggers URL enrichment.
`"cli_ascii"` strips unsupported media. Profiles compose:
`"html+media_url"` applies both transforms.


### Bootstrap (`bootstrap.py`)

Assembly-time wiring, not runtime logic. `build_service_gateway` creates an
orchestrator, registers the default controller set, applies default endpoint
policies, and returns a configured `ServiceGateway`. This is where the service
package becomes a usable, configured boundary surface. Bootstrap should be called
once at startup; calling it per-request would re-register controllers and
re-create the gateway.


### GatewayRestAdapter (`rest_adapter.py`)

Thin normalization layer between transport code and the gateway. Provides
`execute_authenticated(api_key, operation, ...)`, `execute_operation(...)`, and
`execute_request(GatewayRequest(...))` so transport routes do not need to know
about `UserAuthInfo`, `GatewayExecuteOptions`, or render-profile mechanics.


### Controllers (`controllers/`)

Small classes that serve as service façades over engine use cases. Controllers
call story/vm APIs, assemble results, and return. They are not domain owners,
not transport handlers, not repositories.

**RuntimeController** — the core story API. Create stories from worlds, resolve
player choices, retrieve journal fragments, query story state, drop sessions.
The largest controller because it owns the story lifecycle surface including
media dereferencing, blocker diagnostics, and journal-to-envelope serialization.

**WorldController** — world catalog and lifecycle. List available worlds,
describe metadata and media, load/unload worlds.

**UserController** — user CRUD. Create users, update profiles, retrieve info,
generate API keys, drop accounts.

**SystemController** — diagnostics. System info (engine version, uptime, world
count), system reset (not yet implemented).

**Controllers are lazy-loaded.** `controllers/__init__.py` uses `__getattr__`
and deferred imports so lower-layer service modules can be imported without
eagerly pulling the full controller stack.

**Controllers return native results.** The convention is `RuntimeInfo` for
runtime acknowledgments and session-status endpoints, `InfoModel` subclasses for
metadata queries, fragment lists for content endpoints, and media-native payloads
for media endpoints. The orchestrator validates the result shape against
`response_type`. Controllers never serialize to JSON or format for a specific
transport.


### Response Vocabulary (`response.py`)

The native result types that controllers return and the orchestrator validates.

**`NativeResponse`** is the union type:
`FragmentStream | InfoModel | RuntimeInfo | MediaNative`. Every endpoint returns
one of these four shapes. The `response_type` on `ApiEndpoint` declares which
shape the endpoint produces, and the orchestrator enforces the contract.

Story/vm produce engine-native objects. Service validates and classifies them
into this small response vocabulary. Gateway and transport adapt them for
specific clients. Wire format is not the same as native response type;
`RuntimeInfo` is a service contract, not an HTTP response schema.

**`RuntimeInfo`** is the acknowledgment/error payload for service operations.
`RuntimeInfo.ok(cursor_id=..., step=..., **details)` for success,
`RuntimeInfo.error(code=..., message=...)` for failure. The `details` field
carries controller-specific data (for example the created ledger reference from
`create_story` or a serialized `RuntimeEnvelope` from `get_story_update`).
Service exceptions are caught by the orchestrator and converted to
`RuntimeInfo.error()` with the exception's `code` attribute.

**`RuntimeEnvelope`** is a structured runtime payload shape for ordered fragment
output plus cursor position, step, redirect trace, and metadata. Controllers may
embed it inside `RuntimeInfo.details` when an operation needs an acknowledgment
wrapper and a transport-ready runtime snapshot together.

**`InfoModel`** is the base for typed metadata payloads: `SystemInfo`, `UserInfo`,
`WorldInfo`, and `ProjectedState`. `ProjectedState` is the canonical ordered
section model for runtime-state surfaces; it is service-native data, not a
journal fragment. These models serialize cleanly for any transport.

**Response type decision flowchart:**

```
Returns narrative fragments?  → CONTENT (FragmentStream)
Needs a RuntimeInfo-style runtime/status envelope?
                             → RUNTIME (RuntimeInfo)
Returns media/assets?         → MEDIA (MediaNative)
Returns metadata?             → INFO (InfoModel subclass)
```


### Exception Hierarchy (`exceptions.py`)

Service-layer exceptions that map to `RuntimeInfo` error codes for expected
domain failures.

| Exception               | Code               | Meaning                              |
|-------------------------|--------------------|--------------------------------------|
| `ResourceNotFoundError` | `NOT_FOUND`        | User, ledger, choice does not exist  |
| `InvalidOperationError` | `INVALID_OPERATION`| Action not valid in current state    |
| `AccessDeniedError`     | `ACCESS_DENIED`    | Insufficient privileges              |
| `AuthMismatchError`     | `AUTH_MISMATCH`    | User context conflicts with auth     |
| `ValidationError`       | `VALIDATION_ERROR` | Input validation failed              |

`AccessDeniedError` is re-raised rather than converted so transport layers can
map it to HTTP 403. All other service errors are converted to
`RuntimeInfo.error()` and returned normally. Programmer bugs and unexpected
infrastructure failures are a separate class; they should surface as real
exceptions, not be swallowed into `RuntimeInfo`.


### Auth (`auth.py`)

Minimal API-key-to-user resolution. `UserAuthInfo` is a frozen dataclass carrying
`user_id` and `access_level`. `user_id_by_key` resolves an API key to a
`UserAuthInfo` via reverse-index cache lookup when available, persistence scan by
matching `content_hash`, and a legacy compatibility fallback.

Auth is deliberately minimal: no sessions, no tokens, no expiration. Richer auth
(JWT, OAuth, session management) is a transport-layer concern that wraps this
primitive.


### Domain Support Modules

Several modules live in service for boundary reasons rather than because they
form a deep architectural subsystem. Each has a clear reason for being here
rather than in a lower layer:

**User (`user/user.py`)** — the user account model. `User(Entity)` with creation
timestamps, a `privileged` flag, and `current_ledger_id` tracking the active
session. User is a lifecycle/session concept, not a narrative entity; stories do
not know about users.

**Media resolution (`media.py`)** — translates engine-native `MediaFragment`
objects into service-facing payload dicts with resolved URLs, inline data, or
JSON content. Media dereferencing requires path config and scope conventions that
do not belong in story's journal handlers.

**WorldRegistry (`world_registry.py`)** — discovers worlds from configured
directories, lazily compiles them into `World` instances on first access, and
handles anthology-style multi-world bundles. WorldRegistry manages world
lifecycle; story's `World` class defines what a world *is*.

---

## Cross-Cutting Design Decisions

### Service Coordinates Use Cases; It Does Not Define Engine Semantics

Controllers contain use-case logic (how to create a story, what choices are
available). The orchestrator manages resource lifecycle (how to load a ledger,
when to persist). The gateway manages external API shape (operation tokens,
render profiles). None of these layers define narrative or execution semantics;
they coordinate between the engine (story/vm) and the outside world (transports).

If you find significant narrative logic in a controller, it probably belongs in
a story system handler. If you find persistence logic in a controller, it belongs
in the orchestrator. If you find transport formatting in a controller, it belongs
in a gateway hook or transport route.

### Two Names for One Endpoint

Service maintains separate internal and external endpoint identities:

- **Internal name:** controller method name (for example `"RuntimeController.resolve_choice"`)
- **External token:** stable operation token (for example `ServiceOperation.STORY_DO`)

Operation tokens are the stable consumer-facing contract. Internal endpoint names
can be refactored freely, controllers renamed, methods moved, logic split,
without breaking external consumers. The mapping lives in one place
(`operations.py`) and is exhaustively testable.

The current operation token values are already canonical and unsuffixed
(`"story.do"`, `"world.list"`, etc.). The old dual-runtime version prefixes have
been retired from the public surface.

### Type Hints as Dependency Declaration

The orchestrator's hydration mechanism uses standard Python type hints as a
dependency declaration language. A controller method that declares `ledger: Ledger`
is saying "I need a ledger; please load one." The orchestrator inspects the
signature at registration time, resolves the binding type, and hydrates
accordingly at execution time.

This is simple dependency injection without a container. It works because the
resource set is small and fixed (`User`, `Ledger`, `Frame`) and the resolution
order is deterministic.

### Response Types Classify, Don't Constrain

`ResponseType` tells the orchestrator and transport layers what *kind* of result
to expect, not what the result *contains*. A RUNTIME endpoint returns
`RuntimeInfo`, which may carry arbitrary `details`. A CONTENT endpoint returns
a fragment list which may contain any fragment type. The classification drives
validation and serialization strategy, not content policy.

### Gateway Hooks Are the Render Pipeline

Post-story-layer rendering (markdown conversion, media URL enrichment, ASCII
stripping) happens in gateway outbound hooks, not in controllers or story
handlers. This keeps render-profile-specific logic composable and out of the
domain path. A controller's output is the same regardless of whether the client
is a web browser or a terminal; the gateway adapts.

### Expected Failures Collapse Into RuntimeInfo

Expected service-layer failures (resource not found, invalid operation, validation
errors) are caught by the orchestrator and converted to `RuntimeInfo.error()`
payloads. This means transport layers do not need exception handling for domain
errors; they always get a well-typed response. `AccessDeniedError` is the one
exception that propagates, because transports must map it to a specific HTTP
status. Programmer bugs and unexpected infrastructure failures are a separate
class and should still surface as real exceptions.

### Persistence Is an Interface, Not a Dependency

The orchestrator accepts `persistence_manager: Any` and interacts through a
small save/load/remove-like protocol (`save`, `get`, `remove`, or mapping-style
fallbacks). The actual storage backend (memory, file, Redis, MongoDB) is chosen
at bootstrap time. Controllers and the orchestrator are testable with a plain
dict as the persistence manager.

---

## Architectural Principles at the Service Layer

### One Direction, No Callbacks

Engine layers never call back into service. Story handlers do not invoke the
orchestrator. VM does not know about users. If a story handler needs something
service-like (for example a world lookup), it goes through the world facet on the
graph, not through the service layer.

### Controllers Are Façades, Not Owners

A controller method should be small enough that its control flow is obvious at
a glance. It should call engine APIs, assemble a result, and return. If it is
doing complex orchestration, that complexity should be in a story system handler
(for narrative logic) or in the orchestrator's hydration/writeback machinery
(for lifecycle logic). Controllers invoke domain logic that lives in story/vm;
they do not own it.

---

## Related Documents

| Document | Location | Status |
|----------|----------|--------|
| Response type matrix | `docs/src/design/service/RESPONSE_TYPES.md` | Current |
| Service layer (v3.7) | `docs/src/design/service/SERVICE_DESIGN.md` | Stale historical note |
| Simplification tracker | `docs/notes/core_vm_story_service_simplification_plan.md` | Current (Waves 0–6 complete) |
| Core design | `engine/src/tangl/core/CORE_DESIGN.md` | Current |
| VM design | `engine/src/tangl/vm/VM_DESIGN.md` | Current |
| Story design | `engine/src/tangl/story/STORY_DESIGN.md` | Current |

---

*See `STORY_DESIGN.md` for the narrative domain layer that service orchestrates.
See `VM_DESIGN.md` for the execution mechanics that controllers invoke.
See `CORE_DESIGN.md` for the timeless primitives that all layers share.*
