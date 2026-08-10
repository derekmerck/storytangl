# Service Architecture

**Status:** Current manager-first contract

**Implementation companion:** `engine/src/tangl/service/SERVICE_DESIGN.md`

## Position in the Architecture

Service is the boundary between applications and the StoryTangl engine. It
owns persistence-backed lifecycle, caller access, explicit public operations,
world loading, and typed responses.

```text
Applications  → CLI, REST, future transports
Service       → lifecycle, auth, persistence, typed operations
Story         → narrative vocabulary, compilation, journal policy
VM            → execution phases, provisioning, traversal, replay
Core          → graph, entity, registry, selector, dispatch
```

Imports flow downward. Service may call Story, VM, and Core; none of those
layers imports Service.

## Canonical Public Surface

`ServiceManager` is the canonical public service object. Its methods are
ordinary explicit Python use cases, including:

- story creation, advancement, update retrieval, and removal;
- supplementary story-info projection;
- user creation, restoration, inspection, and mutation;
- world and system inspection;
- optional world loading, media access, and administrative operations in the
  local implementation.

`@service_method(...)` attaches bounded descriptive metadata to those methods:
access class, context class, writeback policy, blocking hint, and optional
capability or operation identifiers. Server and client adapters may derive
routing and policy from that metadata, but the metadata is not an endpoint
interpreter.

`build_service_manager(...)` constructs the configured implementation:

- `ServiceManager` for local, persistence-backed execution;
- `RemoteServiceManager` for the supported REST subset through the same
  manager-shaped interface.

Remote mode is a transport adapter. The server remains authoritative for
worlds, users, ledgers, and story sessions.

## Resource Lifecycle

| Resource | Lifetime | Identity | Authority |
|---|---|---|---|
| `User` | persistent | UUID | persistence + Service |
| `Ledger` | persistent | UUID | persistence + Service |
| `Frame` | per operation | derived from a ledger | VM runtime |
| `World` | loadable singleton | label | `WorldRegistry` + Story |

`ServiceManager.open_session(...)` is the canonical operation scope. It
resolves a user and ledger, derives a fresh frame, yields a `ServiceSession`,
and applies the declared writeback policy on exit. Service does not expose a
generic path-based resource binder or a second session object model.

`WorldRegistry` discovers and loads worlds. Service controls availability and
lifecycle; the `World` remains the authority for its templates, mechanics,
domain policy, and story creation.

## Response and Delivery Contract

The public payload vocabulary is typed:

- story-session operations return `RuntimeEnvelope`;
- `RuntimeEnvelope.fragments` contains the actual `BaseFragment` descendants
  emitted through the journal pipeline;
- supplementary reads return models such as `ProjectedState`, `UserInfo`,
  `WorldInfo`, and `SystemInfo`;
- mutation acknowledgements return `RuntimeInfo`.

Service does not translate fragments into a second narrative representation.
Transport adapters own wire serialization, media URL shaping, and other
client-specific presentation.

Story-info is the supplementary projection channel. Providers may contribute
typed `ProjectedSection` values, but those values are disclosed views rather
than authority state. A client hint or hotspot never bypasses ordinary action
selection for mutation.

## Extension Boundary

Service delivers engine output; it does not select or implement story
mechanics. An authored `World` chooses its top-level mechanics and provides
world policy, catalogs, templates, resources, and special handlers. Mechanics
may depend on other mechanics and register against public Story/VM seams.

The REST server and other applications consume the resulting manager contract.
They do not import a credential game, sandbox rule, or media generator merely
to transport its fragments.

## Historical Service Stack

The v3.7 Orchestrator, `ApiEndpoint`, controller, gateway, resource-binding,
operation-token, and path-based writeback designs have been removed. They are
historical migration context, not alternate public APIs. Git history and the
migration notes preserve that work; current documentation should not reproduce
its tutorials or examples as live guidance.

## Current References

- The implementation-adjacent details live in
  `engine/src/tangl/service/SERVICE_DESIGN.md`.
- The generated public method catalog is in the
  [Service API](../../api/service/index.rst).
- Typed response vocabulary is summarized in
  [Response Types](RESPONSE_TYPES.md).
