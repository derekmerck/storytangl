# Credentials Phase 6c: Authored Catalog And Skin Vocabulary

## Status

Approved design handoff. Implementation has not started.

## Implementation prompt

Implement the next credentials-convergence slice after Phase 6b. The capability is:

> A world can author credential definitions and skin vocabulary as data, while the
> credentials kernel continues to operate on stable semantic identifiers and the
> existing facet/game lifecycle.

Read `ARCHITECTURE.md`, `agents.md`, this file,
`PHASE_6B_REQUEST_DOCUMENT_HANDOFF.md`, `CREDENTIAL_ASSEMBLY_RETROFIT.md`,
`mechanics/assembly/COMPONENT_DESIGN.md`, the Phase B section of
`mechanics/games/CREDENTIALS_LOOP_DESIGN.md`, `loaders/compiler.py`,
`loaders/compilers/asset_compiler.py`, and `story/STORY_DESIGN.md` before editing.

Use the existing world compilation and asset-authority seam. Add the smallest generic
world asset-source declaration needed for a YAML mapping of singleton definitions, and
make `AssetCompiler` load it into the world's existing assets facet. Do not add a
credentials-specific manifest field, a second YAML loader, a catalog-plugin registry,
or import-time world-module side effects. Resolve the declared singleton kind through
the world/domain class registry already assembled by `WorldCompiler`.

Convert `worlds/credential_gate/credential_types.reference.yaml` into live authored
input through that path. Each entry must lower to a `CredentialDefinition`, including
its exact `choice / giver / request_document` facet where appropriate. Generated
defaults remain the fallback for worlds that do not provide a catalog.

Make the live file conform to the actual model rather than teaching the generic loader
credential aliases. `name`, allowed origin ids, validity period, issuer/seal group,
`document_kind`, indication id, `requires_id`, and facets are legitimate immutable
definition data and may be added as small typed `CredentialDefinition` fields. They do
not acquire expiration or seal-validation behavior in this slice. Reject unknown
catalog fields instead of silently dropping reference data.

Give an authored credentials game/packet an explicit catalog namespace rather than
looking for an ambient “current world.” Thread that namespace through the existing
setup/case-arrival materialization call. `_definition_for()` must select one loaded
definition in that namespace by the current document coordinates (`document_kind`,
`indication`, and `requires_id`), or honor an explicit definition ref when authored
packet data needs to distinguish two documents with the same coordinates. A configured
catalog with no unique match is an authoring error; it must not silently fall back to a
generated default. No catalog configured means the existing generated-default path.

Untie world coordinates from the fixed checkpoint enums. Credential origin and
indication fields become opaque authored string identifiers throughout the packet,
restriction, factory, roster, story-info, and game paths. `RestrictionLevel`,
`CredentialStatus`, failure semantics, finding semantics, and the normalized operation
code `request_document` remain mechanic-owned. Existing `Region` and `Indication`
constants may remain temporarily as string-valued convenience vocabulary for current
callers, but they must no longer define or validate the complete legal identifier set,
and runtime logic must compare identifiers by equality rather than enum identity.

Add a small data-only credentials presentation profile used by
`CredentialsGameHandler` to realize the existing `request_document` operation. The
profile supplies authored indication/document labels and the choice/journal wording for
the existing request outcomes. Its defaults must reproduce the checkpoint behavior.
Do not put labels, prose, accepts, validity predicates, or outcome policy in the facet.
Do not create a skin-specific handler subclass.

Prove the boundary with two compiled fixtures:

1. `credential_gate` loads its real catalog and preserves its current semantic moves,
   disclosure behavior, dispositions, and visible checkpoint wording.
2. A minimal Hall Monitor fixture uses school-owned origin and indication identifiers,
   school document names, and school wording. It produces the same normalized
   `request_document` move and cleared/verified/confirmed outcomes through the same
   handler, but different `ChoiceFragment` and journal text.

The Hall Monitor fixture is a conformance proof, not the full demo world. Do not convert
the other mediation moves, retire flat `CredentialCase` fields, add credential media,
or build the full school rules/calendar system in this slice.

Run focused loader, credential packet, credentials game, story-info, integration, and
graph-round-trip tests, then the full engine suite. Update this note,
`CREDENTIAL_ASSEMBLY_RETROFIT.md`, and the credential-gate README with the exact landed
contract.

## Why this is the next slice

Phase 6b proved that a visible graph credential can donate one semantic operation:

```text
CredentialDefinition facet
  -> CredentialComponent provenance
  -> CredentialPacketManager gather
  -> CredentialsGameHandler
  -> existing move / UPDATE / finding / journal lifecycle
```

Repeating that work for `verify_id` would exercise the same carrier, channel, consumer,
and realization. It would not prove mechanics convergence. The stronger second proof is
that another world can author different nouns and prose while preserving the same
operation and resolution.

Today three things prevent that proof:

- credential definitions used by the live demo are generated in Python rather than
  compiled from the reference catalog;
- `Region` and `Indication` enumerate checkpoint content such as `foreign_east`,
  `travel`, and `weapon` inside the engine;
- `CredentialsGameHandler` hard-codes checkpoint wording for the operation it now
  discovers semantically.

Phase 6c removes those three constraints without changing the game kernel.

## Canonical boundaries

### Authoring and compilation

The existing path is:

```text
WorldBundle / WorldManifest
  -> WorldCompiler
     -> DomainCompiler
     -> AssetCompiler
     -> WorldBuilder
  -> World.assets
```

`AssetCompiler` is the chokepoint for authored singleton catalogs. It is currently a
small placeholder, which is preferable to creating another loader. Add one explicit
source shape, conceptually:

```yaml
assets:
  - asset_kind: CredentialDefinition
    source: credential_types.yaml
```

The exact field spelling may follow nearby loader conventions, but the contract is one
generic asset-kind-plus-source declaration. The compiler reads the YAML mapping, resolves
`CredentialDefinition` from the already loaded world class registry, and constructs the
catalog through the singleton's ordinary constructor/load path. It does not teach the
generic loader credential fields or add data-driven runtime casting.

The compiled definitions should remain available through the existing world assets
authority. Do not add another global catalog registry or make the credentials mechanic
import story/loaders upward.

Runtime packet construction must not reach upward into `World` or `WorldCompiler` to
find that authority. The world config supplies the stable catalog namespace to its
`CredentialsGame`; the credentials layer resolves the already-loaded singleton
definitions through its own typed catalog using `Selector`, not an ad hoc loop or
`getattr` probing. This keeps world compilation responsible for loading and mechanics
responsible for consuming definitions it has explicitly been configured to use.

### Process-global Singleton identity

`CredentialDefinition` instances are process-global per concrete class and token
references serialize as `(kind, label)`. World-authored local labels therefore need a
stable internal qualification, for example:

```text
credential_gate:work_permit
hall_monitor:work_permit
```

The YAML key remains the local authored id; the compiler derives the qualified singleton
label from world identity. Display names remain authored content and must not be inferred
from the qualified label.

Compilation must be idempotent in one process:

- first compile creates the qualified singleton;
- recompiling the same world with equivalent data reuses it;
- the same local id in another world creates a distinct qualified singleton;
- conflicting data for an already-qualified label is a compile error;
- compiling a world must never clear a singleton registry used by another live world or
  story.

This qualification is required by the existing Singleton contract; do not create
world-specific `CredentialDefinition` subclasses or change singleton persistence in this
slice.

### Authored identifiers

The mechanics relation is:

```text
(origin_id, indication_id) -> RestrictionLevel
credential.indication_id   -> presented evidence for that rule coordinate
```

The kernel does not need to know that an origin means `foreign_east` or `lower_school`,
or that an indication means `work`, `medicine`, or `academic_records`. Use explicit
aliases such as `OriginId = str` and `IndicationId = str` if they improve signatures.

Update all canonical credential surfaces consistently:

- `CredentialDefinition` and `CredentialToken`;
- `ContrabandItem`;
- `RestrictionRule`, `Restrictions`, and their lookup/input helpers;
- `CredentialPacketProtocol` and both packet-manager representations;
- `CredentialCase`, factory/degrade logic, roster/shift specs, story-info, and journal
  detail payloads;
- default/demo catalogs and tests.

Catalog selection is configuration, not hidden process state. A minimal shape is a
`catalog_namespace: str | None` on the authored credentials game (passed into packet
materialization) plus an optional `definition_ref` on the compatibility credential
value when an author must select a specific carrier. Do not infer a world from global
singleton contents, the current working directory, or import order.

String identifiers must round-trip directly and remain JSON-safe. Replace `.value`
projections and enum `is` comparisons on these two axes with direct string use and
equality. Do not replace the enums with a new graph entity hierarchy: these are catalog
coordinates, not durable story actors or components.

The distinction between a purpose/intention and a controlled item remains explicit in
the authored catalog or the field where the identifier is used. Do not recover it by
checking membership in a fixed engine set of checkpoint indications.

### Semantic operation versus skin realization

The semantic contribution remains exactly:

```python
ComponentFacet(
    channel="choice",
    facet_type="giver",
    payload="request_document",
)
```

The game handler still owns stage gating, deduplication, validation, time cost, outcome
resolution, finding state, and journal event selection. The skin profile only supplies
wording for known semantic coordinates. A minimal data shape may contain:

```yaml
indication_labels:
  work: work
move_labels:
  request_document: "Request reissue of {document}"
outcome_text:
  request_document_cleared: "The candidate produces a corrected copy."
  request_document_verified: "The candidate re-presents the same sound document."
  request_document_confirmed: "No valid copy is forthcoming."
```

The exact model name is less important than these constraints:

- it is a small Pydantic/value model, not a handler or registry;
- it persists with authored game configuration through constructor form;
- formatting uses an explicit small set of fields such as `document` and `indication`,
  not arbitrary expressions;
- missing overrides fall back to the current checkpoint defaults;
- the same normalized outcome code selects different skin text;
- the profile cannot observe hidden credential status during availability.

Document nouns belong to the authored credential definition/catalog. Operation phrases
and outcome prose belong to the presentation profile. Neither belongs in
`ComponentFacet.payload`.

## Reference skins

The existing checkpoint reference catalog and Hall Monitor schema should be treated as
two examples of one authoring contract:

| Coordinate | Checkpoint | Hall Monitor |
| --- | --- | --- |
| origin | local / foreign region | upper / lower / exchange program |
| intention | travel / work / emigrate | academic / activity / off-campus |
| controlled item | weapon / drugs / secrets | uniform / medicine / records |
| identity document | passport / state id | student id |
| authorization | visa / permit / waiver | hall pass / activity pass / doctor's note |
| allow | admit | allow onward |
| deny | turn back | send back |
| arrest | detain | send to office |

The engine owns the normalized restriction and operation grammar. Each catalog owns the
cardinality and names of its coordinates. Three-by-three symmetry in a demo remains an
authoring choice, never a schema constraint.

## Expected edit surface

- `tangl/loaders/manifest.py`, `bundle.py`, `compiler.py`, and
  `compilers/asset_compiler.py`
  - add and compile one generic singleton asset-source declaration;
  - retain compiled definitions through `World.assets`.
- `tangl/mechanics/credentials/domain.py` and `assembly.py`
  - accept authored string coordinates;
  - add the small immutable name/origin/period/issuer fields required to preserve the
    live catalog without loss;
  - preserve exact facet templates and default-catalog fallback.
- `tangl/mechanics/games/credentials_*`
  - migrate origin/indication use to opaque ids;
  - thread explicit catalog selection through setup/case-arrival materialization;
  - add data-driven request-document realization without changing resolution.
- `worlds/credential_gate`
  - make the reference catalog live and preserve checkpoint behavior.
- focused loader, credentials, service/story-info, integration, and persistence tests
  - add two-world collision/idempotency and two-skin parity proofs.

Do not broaden generic loaders beyond the one concrete source form needed here. If the
existing world asset seam cannot retain the compiled catalog without a second authority,
stop and surface that architectural mismatch rather than hiding it in the credentials
package.

## Acceptance matrix

| Concern | Required evidence |
| --- | --- |
| Canonical loading | one WorldCompiler/AssetCompiler path; no direct world YAML reads or import side effects |
| Singleton identity | stable world-qualified labels; same-world idempotency; two-world isolation; conflict diagnostic |
| Catalog selection | explicit game/packet namespace; unique coordinate match or explicit definition ref; no ambient-world lookup |
| Open vocabulary | school-owned string origin/indication ids pass without engine enum additions |
| Facet parity | authored checkpoint definition contributes the same exact 6b facet and move |
| Semantic secrecy | visible existence controls availability; hidden status only affects committed outcome |
| Syntactic variation | checkpoint and Hall Monitor emit different choice/journal text for the same move/outcome codes |
| Persistence | catalog is available before `Graph.structure()`; restored tokens resolve qualified definitions |
| Lifecycle | compilation/setup creates definitions/components; repeated PLANNING remains pure |
| Compatibility | no-catalog worlds retain generated defaults; existing checkpoint behavior remains stable |
| Scope | no full Hall Monitor world, other mediation conversion, media, flat-field retirement, or generic facet pipeline |

## Explicitly deferred

- Full Hall Monitor demo rules, schedules, demerits, and story consequences.
- Facet conversion of `verify_id`, search, disclosure, relinquish, or dispositions.
- Piece-based document selection and document-identity receipts.
- Credential card media and presence-bound portraits.
- Retirement of flat `CredentialCase` packet fields.
- Promotion of the facet payload string into a richer universal operation type.
- Robot/chopshop and sandbox consumers.

The immediate follow-up after this slice should be the full Hall Monitor conformance
world. Only after the manager-backed authored checkpoint and Hall Monitor paths run side
by side should Phase 7 remove the flat compatibility representation.
