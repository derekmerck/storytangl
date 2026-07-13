# Credentials Phase 6a: Token Facet Bridge Contract

## Status

Implemented for the Phase 6a pure-discovery milestone only. No credential game
integration is implemented by this contract.

## Intent and constraints

- **Capability:** prove that an owner-bound credential packet can *purely discover*
  facets supplied by its credential tokens, retaining document and packet-slot
  provenance. This is the prerequisite to any credentials move contribution.
- **Applicable invariants:** facets are context-bound value data, not graph members or
  a dispatch system. PLANNING reads are repeatable and do not prepare packets, mutate
  game state, add actions, or reveal hidden document state. The existing game handler
  remains the move/choice factory; UPDATE remains the only write boundary.
- **Canonical chokepoints:** reuse `ComponentFacet`,
  `SlottedContainer.component_facets()`, and `CredentialPacketManager`; later reuse
  `CredentialsGameHandler.get_available_moves()` / `get_provisioned_moves()` and the
  existing `HasGame` PLANNING/UPDATE handlers. Do not add a credentials phase bus,
  registry, serializer, or action factory.
- **Persistence:** credential tokens remain graph members and packet membership remains
  UUID-backed through the owner-bound manager. Any persistence proof is
  `Graph.unstructure()` / `Graph.structure()`, never a Pydantic dump/validate pair.
  A world using facet-bearing `CredentialDefinition` singletons must load that authored
  catalogue before graph structure; fresh-process restoration must not depend on a
  singleton created incidentally at runtime. Generated default definitions may remain
  facet-free.

## Context selected

- `devref` was rebuilt with the project Python (`862` sources, `3,703` artifacts). Its
  `credentials assembly facet` search and `assembly` map identify
  `ComponentFacet`, `SlottedContainer`, `ComponentManager`, `CredentialDefinition`,
  `CredentialComponentToken`, and `CredentialPacketManager` as the relevant current
  code, with `COMPONENT_DESIGN.md` as design context. The sources below were then
  checked directly.
- **Canonical current code:**
  `mechanics/assembly/component.py` (`ComponentFacet` and `Component`),
  `mechanics/assembly/base.py` (slot-aware facet gather and provenance),
  `mechanics/credentials/assembly.py` (the Token-wrapped credential component and
  packet manager), `mechanics/games/credentials_game.py` (choice factory), and
  `mechanics/games/handlers.py` (the existing game PLANNING/UPDATE path).
- **Canonical tests:** `engine/tests/mechanics/test_assembly.py` and
  `engine/tests/mechanics/credentials/test_credential_packet_manager.py`.
- **Design notes, not current behavior:** `COMPONENT_DESIGN.md` describes intended
  channel/handler adoption; `CREDENTIAL_ASSEMBLY_RETROFIT.md` defers Phase 6 until the
  contribution contract is settled. Neither establishes a live VM facet consumer.

## Current contract and gap

`ComponentFacet` currently supplies only `channel`, `facet_type`, opaque `payload`,
and optional `source_id` / `subject_id`. Its `matches()` filters the first two; its
`with_provenance()` fills missing provenance. `Component.component_facets()` supplies
its own UID as source, while `SlottedContainer.component_facets()` supplies its slot
name as subject. The assembly tests prove that a consumer may fold those returned data
objects, but no VM, provisioning, or choice handler gathers them today.

`CredentialComponent` cannot use that path directly: it is a `Token` wrapper over
`CredentialDefinition`, not a subclass of `Component`; it has neither `facets` nor
`component_facets()`. The packet manager's generic gather consequently reaches a
method that credential tokens do not provide. Making credentials a second component
hierarchy or adding a credentials-only handler would violate the reuse boundary.

## One milestone: pure token-to-packet discovery proof

- **Allowed surfaces:** `credentials/assembly.py`, narrowly focused credential/assembly
  tests, and this contract's status if implementation is later approved. No VM,
  `HasGame`, game-handler, journal, widget, or persistence-framework edits.
- **Facet data:** authored, immutable facet templates belong on the
  `CredentialDefinition` singleton catalogue. They are not copied into packet state,
  cached as derived state, or stored on `CredentialCase`. Per-document facts such as
  status remain on the `CredentialComponent` token; this milestone does not define
  dynamic activation from those facts.
- **Bridge:** `CredentialComponentToken` exposes the same narrow
  `component_facets(channel=..., facet_type=..., subject_id=...)` read protocol as
  `Component`. It derives each returned template's `source_id` from the token's UID.
  The existing `CredentialPacketManager.component_facets()` gather then supplies the
  assigned slot as `subject_id`. It returns copied value objects and never alters the
  definition template, token, manager, game, or graph.
- **Proof:** assign one graph credential token whose definition has one opaque test
  facet into a packet slot; gathering by channel returns that payload with
  `source_id == str(token.uid)` and `subject_id == slot`. Repeating the same read
  returns equivalent data and leaves packet assignment IDs, token state, and graph
  constructor form unchanged. Mutating the gathered facet must not alter the authored
  singleton template or a later gather result. A fresh-process graph round-trip fixture
  must load its facet-bearing definition catalogue before `Graph.structure()` and then
  prove the restored token resolves the authored definition. The existing owner-bound
  graph round-trip test remains the persistence guard; do not add
  `model_dump()`/`model_validate()` as evidence.
- **Validation when implemented:**
  `poetry run pytest engine/tests/mechanics/test_assembly.py engine/tests/mechanics/credentials/test_credential_packet_manager.py`

## Explicitly deferred: choice and writeback integration

The first consumer must be a separate approved slice. It may let
`CredentialsGameHandler` inspect the active packet's *visible* credential facets and
create its own `CredentialsMove` values through its existing move factory. The generic
`HasGame` PLANNING handler then continues to project those moves into dynamic actions;
it is not a facet consumer or factory. UPDATE continues through `process_game_move()`
and the game handler, with atomic multi-object effects delegated to `TransactionOffer`
when needed.

That slice must decide the credential-specific payload schema, duplicate/override
policy, labels/accepts, selected-move validation, receipt/journal provenance, and
whether a mutation requires a transaction. It must prove that visibly equivalent valid
and invalid documents give the same menu, that repeated move discovery is pure, and
that a selected action writes exactly once in UPDATE.

## Unresolved design decisions

The shared VM/choice contribution contract is **not sufficiently settled** for live
adoption. `ComponentFacet` has no `when`, target selector, fold/precedence rule,
parameterized-choice contract, or phase-safe `vm_phase` payload schema; the design
notes describe these as future intended shape rather than implemented behavior. Phase
6a therefore authorizes only opaque discovery. It deliberately does not choose between
`channel="vm_phase"` data and lowering into existing dispatch, and it does not let
facets register handlers or generate actions themselves.

## Review matrix

| Surface | Required evidence |
| --- | --- |
| Architecture/reuse | Token adapter feeds existing manager gather; no new dispatch or lifecycle path |
| Provenance | Token UID is source; manager slot is subject; templates remain unmodified |
| Lifecycle | Repeated discovery is pure; setup/UPDATE, not read discovery, owns materialization and writes |
| Persistence | Catalogue is loaded before structure; graph round-trip retains authored singleton resolution, one member per token, and UUID slot references |
| Integration | Deferred slice proves handler-owned visible-choice factory and UPDATE-only writeback |

## Workflow observation

Phase 5's sampled-offer preparation and `game_state` constructor-form work are
prerequisites assumed by this contract, not surfaces to recreate or modify.
