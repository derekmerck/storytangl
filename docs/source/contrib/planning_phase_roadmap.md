# Planning Phase Data Path Roadmap

> Reference implementation priorities: **generic contracts**, **deterministic behavior**, **traceable receipts**.
>
> Goal for v3.7: close the loop from frontier requirements → offers → applied updates → receipts so ledger/phase bus deliver a complete audit trail before domain-specific builders arrive.

## Current Baseline

- **Phase bus contract** – `Frame.run_phase` already pipelines handlers per `ResolutionPhase`, clearing `Context.job_receipts`, aggregating with the reducer declared by each phase, and caching per-phase outcomes for later reducers.【F:engine/src/tangl/vm/frame.py†L187-L212】
- **Context plumbing** – `Context` is frozen, exposes the working graph/cursor/scope, carries deterministic RNG, and buffers job receipts for downstream selectors.【F:engine/src/tangl/vm/context.py†L21-L114】
- **Planning primitives** – Requirements, offers, provisioners, and receipts are in place: requirements validate policy/template pairs, provisioners can locate/update/create/clone providers, offers call provisioners, and receipts summarize accepted work and unresolved hard requirements.【F:engine/src/tangl/vm/planning/requirement.py†L22-L142】【F:engine/src/tangl/vm/planning/provisioning.py†L1-L165】【F:engine/src/tangl/vm/planning/offer.py†L24-L187】
- **Default handlers** – The reference planning handlers already implement a collect → select/apply → summarize pipeline and register with the global domain so they participate in the planning phase bus.【F:engine/src/tangl/vm/planning/simple_planning_handlers.py†L1-L93】
- **Ledger integration** – The ledger can spawn frames, push snapshots, and append patches/journal entries, but it expects the planning phase to surface a `PlanningReceipt` so downstream projection/commit can audit the decision trail.【F:engine/src/tangl/vm/ledger.py†L15-L103】

## Gaps & Open Questions

1. **Offer lifecycle & scope awareness**
   - Affordances are noted as TODOs and currently ignored, so frontier resources are never surfaced before dependency provisioning.【F:engine/src/tangl/vm/planning/simple_planning_handlers.py†L32-L36】
   - Offers do not yet encode scope-specific selectors (policy, domain ownership, resource availability), which we will need once multiple domains compete to satisfy the same requirement.

2. **Selector policy & arbitration**
   - Selection currently collapses purely by priority and first-come order; we have no way to flag conflicts on shared provider attributes or to escalate unresolved hard requirements beyond the summary list.
   - There is no explicit representation of “no viable offer” vs. “waived soft requirement”; the selector relies on offer return flags, but we should log waived soft requirements for diagnostics.

3. **Builder integration**
   - Provisioners run directly off the graph registry; domains cannot yet inject additional registries/templates or rewrite requirements before provisioning.
   - Builders cannot publish additional receipts beyond the `BuildReceipt`, so we lose diagnostics (e.g., which domain satisfied a requirement, what heuristics were applied).

4. **Phase output plumbing**
   - Planning receipts are returned, but the phase bus/ledger do not yet relay them into the record stream or expose them alongside patches/fragments; projection/commit code will need deterministic access to the summarized plan before journaling.
   - Event-sourced runs rely on watchers capturing mutations during offer acceptance, yet we do not reset the context between planning and update phases, so patch generation may include “preview” mutations unless we snapshot boundaries explicitly.

5. **Testing & diagnostics**
   - No scenario tests cover the planning triplet; regressions in offer aggregation or receipt composition would go unnoticed.
   - We also lack developer tooling to inspect per-phase receipts (e.g., a lightweight trace view in `Frame` or `Ledger`).

## Recommended Next Steps

1. **Complete offer collection**
   - Extend `plan_collect_offers` to enumerate visible affordances in scope order, optionally preferring them before dependencies, and emit offers tagged with domain/source metadata so selectors can differentiate provenance.【F:engine/src/tangl/vm/planning/simple_planning_handlers.py†L32-L50】
   - Allow domains to register additional collectors at different priorities to decorate requirements (e.g., inject fallback templates, clone policies).

2. **Formalize selector arbitration**
   - Introduce a selector helper (e.g., `OfferSelector`) that groups offers by `(requirement, conflict_key)` and enforces policy (priority, hard vs. soft, conflict resolution). It should produce explicit outcomes: accepted offer, waived soft requirement, or unresolved hard requirement with diagnostics.
   - Extend `BuildReceipt` or add a companion record so each decision logs the selector that acted, the domain responsible, and the conflict key considered.【F:engine/src/tangl/vm/planning/offer.py†L24-L187】

3. **Wire builder hooks into scope**
   - Let the context expose domain-provided registries/templates to provisioners (e.g., via `Scope.get_handlers(is_instance=Provisioner)`), so requirement resolution can search beyond the base graph.【F:engine/src/tangl/vm/context.py†L86-L114】【F:engine/src/tangl/vm/planning/provisioning.py†L37-L165】
   - Support pre-resolution requirement transforms (policy normalization, criteria enrichment) by letting builders register preprocessors that run before offer creation.

4. **Surface planning receipts to the ledger**
   - After `Frame.run_phase(P.PLANNING)`, push the resulting `PlanningReceipt` into `Frame.records` (likely as a note/fragment) so the ledger’s record stream captures the plan alongside patches and journal fragments.【F:engine/src/tangl/vm/frame.py†L187-L212】【F:engine/src/tangl/vm/ledger.py†L15-L103】
   - When event sourcing is enabled, ensure watchers reset between planning and update so the `Patch` reflects applied offers precisely (or alternatively separate planning mutations from finalization mutations via sub-patches).

5. **Add regression scaffolding**
   - Build scenario tests around a toy graph with one dependency and one affordance to assert that collectors, selectors, and receipts behave deterministically (e.g., unresolved hard requirements propagate, soft waivers are logged, accepted offers mutate the graph once).
   - Provide a developer trace helper (perhaps `Frame.inspect_phase(phase)` or an enriched debug log) that prints collected offers, chosen providers, and resulting receipts to ease future debugging.

6. **Document handler extension patterns**
   - Capture the offer/selector lifecycle and extension points in the docs so future domain builders know where to plug in specialized logic (collectors, selectors, provisioners, receipt enrichers). This roadmap can seed a deeper section in the contributor guide once the implementation lands.

Following this order keeps the reference stack generic while delivering the audit trail we need before layering on concrete narrative domains.
