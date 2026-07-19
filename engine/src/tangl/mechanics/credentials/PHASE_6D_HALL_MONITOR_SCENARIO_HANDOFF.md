# Credentials Phase 6d: Hall Monitor Scenario Conformance

## Status

**READY FOR IMPLEMENTATION (2026-07-19).** Phase 6c landed in PR #311 with named,
bounded world catalogs, world-local `catalog_ref` selection, qualified persistence
identity, open origin/indication coordinates, and skin-aware `request_document`
realization. Its temporary Hall Monitor fixture proves catalog and wording isolation,
but it is not a playable world and does not prove the lower half of the mechanics
adoption model.

Phase 6d proves:

```text
World authority
  -> scenario type
     -> configured scenario instance
        -> materialized encounters
```

## Implementation prompt

Implement the next credentials-convergence slice after Phase 6c. The capability is:

> A real Hall Monitor world adopts the credentials mechanic through a bespoke scenario
> type, a script invocation configures one shift, and that shift materializes generated
> and pinned student encounters through the same packet, disposition, game-handler, and
> persistence lifecycle as the border checkpoint while projecting school vocabulary.

Read `ARCHITECTURE.md`, `agents.md`, this file,
`PHASE_6C_AUTHORED_CATALOG_HANDOFF.md`, `CREDENTIAL_ASSEMBLY_RETROFIT.md`, the Phase A,
Phase B, and Hall Monitor sections of `mechanics/games/CREDENTIALS_LOOP_DESIGN.md`,
`mechanics/assembly/COMPONENT_DESIGN.md`, `story/STORY_DESIGN.md`, and the live
`worlds/credential_gate` bundle before editing.

Create a real, discoverable `worlds/hall_monitor` bundle. Its manifest exposes a named
`school` `CredentialDefinition` catalog through the generic asset path landed in Phase
6c. Use school-owned coordinates such as `upper`, `lower`, and `exchange` origins;
`academic`, `activity`, and `off_campus` intentions; and `uniform`, `medicine`, and
`records` controlled-item indications. These are authored identifiers, not additions to
engine enums.

Add a world-domain scenario type such as `HallMonitorCredentialsGame` hosted by a
`HallMonitorBlock`. The type fixes `catalog_ref="school"`, supplies the ordinary school
restriction map, chooses which existing credentials actions and dispositions participate,
and supplies school presentation defaults. It may contain deliberate domain code and
policy overrides. Do not force distinctive Hall Monitor logic into a generic YAML rule
interpreter, and do not create a skin-specific copy of the credentials handler when the
existing handler plus scenario configuration is sufficient.

Make one script block a genuine scenario instance rather than merely selecting the block
class. It must author at least the encounter count, expected-disposition distribution,
and deterministic seed through a small Hall Monitor block/game configuration surface.
Include at least one bespoke or recurring student encounter through the existing pinned
offer/case seam. Keep this authoring surface world-local unless implementation proves a
second engine consumer needs a generic scenario-spec abstraction.

Generate the remaining encounters through the existing `ShiftSpec` -> `ScenarioOffer` ->
`materialize()` funnel. Every generated encounter begins with a nominally conforming
packet, receives a compatible degradation for its sampled expected disposition, and is
verified through the same `derive_disposition()` / `expected_disposition()` chokepoint.
Materialize graph components and bind packet managers at setup or case-arrival UPDATE,
never during repeated PLANNING reads.

Extend `CredentialPresentationProfile` only as far as needed to project the complete
Hall Monitor loop. In addition to the already-skinned `request_document`, it may provide
scenario wording for known semantic move kinds, disposition labels, generated document
descriptions, and status/finding realization. The same existing logical state may render
as a missing teacher signature in school and a missing issuing stamp at the border.
Policy, validity, hidden-information availability, time cost, and outcomes remain outside
the presentation profile.

Do not introduce a second defect/status model in this slice. `CredentialStatus`,
`FailureMode`, and the flat narrative fields remain compatibility surfaces until packet
identity is fully manager-backed. Generated school encounters should project their
structured packet truth through the selected presentation profile rather than teaching
`credentials_factory.render_narrative()` more school-specific branches. Use the smallest
dependency-safe call direction: the factory builds/degrades logical data; the scenario or
game layer supplies realization data after materialization.

Preserve the current checkpoint defaults byte-for-byte where practical and behaviorally
everywhere. A default `CredentialsGame` and `worlds/credential_gate` must retain their
existing move labels, finding prose, scoring, outcomes, and journal flow.

Run focused Hall Monitor, loader, roster-generation, credentials-game, packet-manager,
story-info, integration, and graph-round-trip tests, then the full engine suite. Update
this note, `CREDENTIAL_ASSEMBLY_RETROFIT.md`, `MECHANICS_FAMILIES.md` if priorities move,
and both demo-world READMEs with the exact landed contract.

## Why this is the next slice

Phase 6c proves the upper boundary:

```text
bound World
  -> exposed named TokenCatalog
     -> scenario-local catalog_ref
        -> bounded CredentialDefinition selection
```

The test-only Hall Monitor fixture deliberately stops there. It manually constructs one
packet and one game to prove that `school` and `border` catalogs can coexist and that
separate worlds cannot see one another's definitions. It does not prove that a bespoke
scenario type can configure a population of encounters and run the full story lifecycle.

The live checkpoint already contains the necessary lower-layer pieces:

- `GateCredentialsGame` / `CredentialGateBlock` provide the scenario-type pattern;
- `ShiftSpec` carries rules, encounter count, distributions, pinned offers, and seed;
- `ScenarioOffer` is the promised encounter with an expected disposition;
- `materialize()` builds and degrades the concrete `CredentialCase`;
- `CredentialPacketManager` owns graph-backed document components on arrival;
- `CredentialsGameHandler` owns inspection, mediation, decision, scoring, UPDATE, and
  journal behavior.

Hall Monitor should rebind those pieces, not create another credentials loop. That is the
convergence proof.

## Four-layer contract

| Layer | Hall Monitor responsibility | Must remain outside |
| --- | --- | --- |
| World | expose the `school` catalog, domain classes, and presentation resources | another loaded world's private catalogs |
| Scenario type | select `school`; define school restrictions, actions, dispositions, scoring defaults, and presentation | encounter count and one run's sampled roster |
| Scenario instance | configure one shift's count, distributions, seed, and special encounters | generic credential resolution semantics |
| Encounter | carry one student, packet, applicable context, degradation, expected disposition, findings, and play state | population distribution and catalog discovery |

The mechanic kernel owns stable operations and resolution. The scenario type may use
hard-coded domain logic. The scenario instance is authored configuration. The encounter
is durable runtime state.

## Reference school vocabulary

The Hall Monitor catalog should preserve the shape of the reference schema while
conforming to the live model:

| Logical role | Example school carrier |
| --- | --- |
| identity | student id |
| anonymous academic authorization | hall pass |
| anonymous activity authorization | activity pass |
| anonymous off-campus authorization | off-campus pass |
| short-term exception | emergency uniform or medical waiver |
| durable academic authorization | student-worker id |
| durable activity authorization | student-athlete id |
| durable medical authorization | doctor's note |
| records authorization | office pass |

Carrier names, validity dates, issuer marks, teacher signatures, and document appearance
are projection. The current credential and restriction fields remain the compatibility
logic used to generate and adjudicate the encounter.

## Scenario-instance proof

The script should visibly configure one shift, conceptually:

```yaml
kind: hall_monitor.domain.HallMonitorBlock
encounters: 5
disposition_distribution:
  pass: 0.50
  deny: 0.30
  arrest: 0.20
seed: 20260719
```

The exact field names may follow nearby model conventions. The important contract is that
these values belong to this block invocation, not to the global mechanic or the school
catalog. The scenario type may project the normalized disposition codes as `allow`,
`send back`, and `send to office`.

Include one pinned special encounter using existing seams. A lower-school student with a
conditional activity pass, an exchange student, or an office-records case is sufficient.
The special encounter may be authored in world domain code if nested script construction
would require new generic loader machinery; the script instance must still control the
ordinary shift configuration.

## Projection boundary

The current generated-case path stores compatibility strings in
`presented_documents`, `hidden_facts`, and `packet_hidden_facts`. Phase 6d may continue to
populate those fields, but their wording must come from scenario presentation after the
logical packet is built and degraded.

Required parity example:

```text
logical status: missing attestation compatibility code

border projection: The issuing stamp is missing.
school projection: The required teacher signature is missing.
```

This is a realization difference only. The player sees the same existence-based choices;
hidden validity is disclosed only by committed inspection or mediation; the same outcome
code drives resolution.

Do not make presentation strings rule inputs. Do not infer status from prose. Do not
place prose or media details in `ComponentFacet.payload`.

## Expected edit surface

- `worlds/hall_monitor`
  - add the real world manifest, domain module, script, school catalog, and README;
  - define the Hall Monitor scenario type and one configured scenario instance.
- `tangl/mechanics/games/credentials_game.py`
  - extend the existing presentation profile and label/journal projection only as needed;
  - retain the handler as interaction and resolution authority.
- `tangl/mechanics/games/credentials_factory.py` and `credentials_roster.py`
  - keep build-correct-then-degrade generation;
  - make generated compatibility narrative scenario-aware without importing world code or
    moving policy into projection.
- loader/integration and focused credentials tests
  - prove world discovery, script configuration, generated/pinned encounter composition,
    semantic parity, projection differences, persistence, and planning purity.

If authoring a scenario instance requires changes to generic `HasGame`, template
materialization, or constructor-form persistence, stop and surface that mismatch. Do not
hide a new generic game-configuration framework inside the Hall Monitor domain module.

## Acceptance matrix

| Concern | Required evidence |
| --- | --- |
| Real world | `WorldRegistry` discovers `hall_monitor`; its script reaches a playable Hall Monitor block |
| World adoption | the scenario resolves the bounded `school` catalog through its bound World |
| Scenario type | a Hall Monitor subtype fixes school catalog/policy/presentation without forking the credentials kernel |
| Scenario instance | one script invocation controls encounter count, disposition distribution, and seed |
| Special encounter | at least one pinned/bespoke student is included through existing roster seams |
| Encounter invariant | every generated materialization derives to its promised expected disposition |
| Packet authority | arriving generated encounters own manager-backed credential components before PLANNING |
| Projection parity | one logical defect/status yields school wording in Hall Monitor and unchanged border wording in Credential Gate |
| Semantic secrecy | menu availability depends on visible evidence, never hidden validity |
| Lifecycle | repeated PLANNING is pure; UPDATE and JOURNAL commit exactly once |
| Persistence | active Hall Monitor game, packet managers, and catalog-backed tokens survive graph round-trip |
| Compatibility | existing credential-gate focused tests and end-to-end shifts remain unchanged |

## Explicitly deferred

- Decomposition or renaming of `CredentialStatus`, `FailureMode`, or `FailureClass`.
- Retirement of flat `CredentialCase` packet and narrative fields; that remains Phase 7.
- Conversion of `verify_id`, search, disclosure, relinquish, or disposition moves into
  component facets.
- Full school calendar, morning/afternoon periods, demerit progression, schedules, or
  recurring-character dossier system.
- Credential media, student portraits, and presence-bound identity comparison.
- Cross-world imports/re-exports and a universal catalog/provider abstraction.
- A generic scenario-spec framework for every mechanic.

## Follow-up

After the manager-backed Credential Gate and Hall Monitor worlds run side by side, Phase
7 may remove the flat packet compatibility representation. Only after that identity
cutover should a later slice replace checkpoint-flavored status/failure names with
normalized evidence defects and connect those defects to richer presence and media
projection.
