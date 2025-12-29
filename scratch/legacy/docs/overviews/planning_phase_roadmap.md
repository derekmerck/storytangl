# Planning Phase Data Path Roadmap

> Reference priorities: **generic contracts**, **deterministic behavior**, **traceable receipts**.
>
> Target for v3.7: deliver an auditable planning cycle that spans frontier requirements → offer discovery → applied mutations → persisted receipts before layering narrative-domain specifics.

## A. Baseline Capabilities (Validated)

| Area | Current Status | Key References |
| --- | --- | --- |
| Phase execution | `Frame.run_phase` sequences handlers per :class:`ResolutionPhase`, resets :class:`Context.job_receipts`, and caches outcomes for later reducers. | :mod:`tangl.vm.frame`【F:engine/src/tangl/vm/frame.py†L187-L212】 |
| Context plumbing | :class:`Context` freezes graph/cursor/scope, exposes deterministic RNG, and buffers job receipts. | :mod:`tangl.vm.context`【F:engine/src/tangl/vm/context.py†L21-L114】 |
| Planning primitives | Requirements, offers, provisioners, and receipts validate inputs, locate providers, and summarise accepted work. | :mod:`tangl.vm.planning.requirement`, :mod:`tangl.vm.planning.provisioning`, :mod:`tangl.vm.planning.offer`【F:engine/src/tangl/vm/planning/requirement.py†L22-L142】【F:engine/src/tangl/vm/planning/provisioning.py†L1-L165】【F:engine/src/tangl/vm/planning/offer.py†L24-L187】 |
| Default planning handlers | The collect → select/apply → summarise pipeline is registered on the phase bus and delivers deterministic receipts. | :mod:`tangl.vm.planning.simple_planning_handlers`【F:engine/src/tangl/vm/planning/simple_planning_handlers.py†L1-L93】 |
| Ledger integration | Ledger spawns frames, appends snapshots, patches, and journals; planning receipts only need to be forwarded to complete the audit trail. | :mod:`tangl.vm.ledger`【F:engine/src/tangl/vm/ledger.py†L15-L103】 |

These pieces already drive an end-to-end planning loop against the existing handler set.

## B. Outstanding Gaps Blocking MVP

1. **Affordance coverage & precedence** – Collectors ignore affordances, so in-scope reusable resources never surface before provisioning new providers.【F:engine/src/tangl/vm/planning/simple_planning_handlers.py†L32-L36】
2. **Scope-aware builders** – `plan_collect_offers` instantiates a bare :class:`Provisioner` instead of discovering provisioners via scope, preventing domain registries or templates from participating.
3. **Planning audit trail** – The :class:`PlanningReceipt` is cached but not persisted alongside patches/journal fragments, leaving the record stream without the “why” for each step.
4. **Event-sourced preview refresh** – When `event_sourced=True`, watcher previews survive from PLANNING into UPDATE/JOURNAL, risking stale graph views during projection unless the context resets between phases.
5. **Finalize contract mismatch** – :class:`ResolutionPhase.FINALIZE` promises a :class:`Patch`, yet handlers return ``None`` and the frame fabricates the patch afterward, so phase outcomes and stream data diverge.
6. **Receipt semantics** – `PlanningReceipt.summarize()` marks every rejected requirement as “unresolved hard” even when `hard_req=False`; there is no counter for waived soft requirements.
7. **Provisioner registry injection** – Domains cannot supply extra registries/templates (e.g., world libraries) into the default :class:`Provisioner` search path.
8. **Developer ergonomics** – :meth:`Context.inspect_scope` exists, but there is no parallel `Frame` inspection hook to dump collected offers, selected providers, and resulting receipts for debugging or doctests.

Items 1–6 are **P0 blockers** for an MVP; 7–8 are **P1 follow-ups** that unlock domain extensibility and developer tooling but can land once the core loop is auditable.

## C. Minimal Implementation Plan (Sequenced)

### P0 — Close the Planning Loop

1. **Affordance-first collection**
   - Extend `plan_collect_offers` to enumerate in-scope affordances before unsatisfied dependencies and tag each :class:`ProvisionOffer.selection_criteria` with `{"source": "affordance"|"dependency"}` for downstream traces.
   - Ensure collectors discovered through scope can opt into earlier priorities without editing the core handler.

2. **Scope-aware provisioners**
   - Replace the hard-coded :class:`Provisioner` instantiation with `ctx.get_handlers(is_instance=Provisioner)` to discover domain-specific builders, appending the default provisioner as a fallback.
   - Allow discovered provisioners to contribute additional registries/templates when evaluating requirements.

3. **Persist planning receipts**
   - After `run_phase(P.PLANNING)` inside :class:`Frame.follow_edge`, append the `PlanningReceipt` to `Frame.records` (structured fragment or note) before JOURNAL executes so each `step-XXXX` marker contains planning + journal + patch artifacts.
   - Update ledger tests to assert the planning note appears between journal fragments and patches for event-sourced runs.

4. **Refresh event-sourced previews**
   - When `self.event_sourced` is true, invalidate/rebuild the preview context after PLANNING and UPDATE so JOURNAL/FINALIZE see the post-mutation graph while the watcher still feeds the final patch.
   - Confirm replay parity by running the event-sourced integration test with `replay()`; expect identical state hashes and matching planning notes.

5. **Align FINALIZE contract**
   - Either (A) keep patch creation in :class:`Frame` but set `phase_outcome[P.FINALIZE]` to the constructed patch (loosening type hints accordingly), or (B) move patch construction into a FINALIZE handler that returns the patch. Option A centralises event logic; Option B makes the phase contract explicit. Choose one path and update reducers/tests to match.

6. **Clarify receipt summarisation**
   - Modify `PlanningReceipt.summarize()` so unresolved hard requirements only include `hard_req=True` failures and add a `waived_soft_requirements` counter/list for diagnostics.
   - Ensure `BuildReceipt` instances always record `hard_req` so summarisation cannot misclassify results.

### P1 — Post-MVP Enhancements

7. **Registry injection hooks**
   - Extend :class:`Provisioner._requirement_registries` (or equivalent) to include registries supplied via scope so planners can search static content libraries alongside the live graph.

8. **Developer trace helpers**
   - Add `Frame.inspect_phase(phase)` (or a debug flag) that dumps collected offers, selected providers, and resulting receipts; use it in doctests and regression logs to simplify onboarding.

## D. Testing & Documentation Commitments

1. **Scenario tests in ``engine/tests/vm/planning/``**
   - Fixture: toy graph with one dependency and one affordance to assert affordance precedence, selection provenance tags, and receipt counters for accepted/waived/unresolved cases.
   - Event-sourced replay: mutate during planning, run with `event_sourced=True`, ensure JOURNAL/FINALIZE observe refreshed previews and the emitted patch matches watcher events.
   - Ledger stream: verify each step emits planning, journal, and patch records under the same marker.

2. **Documentation update (post-implementation)**
   - Expand the contributor guide with an “Extending planning” section covering collector/selector registration, provisioner injection via scope, and interpreting planning receipts during replay.

## E. Acceptance Checklist for the MVP Slice

- Every frame step emits three artifacts under a shared `step-XXXX` marker: planning receipt, journal fragments, and patch (when event-sourced).
- Running an event-sourced ledger through replay reproduces the same state hash and the planning note explains the applied offers.
- Affordance-first collection can satisfy dependencies without provisioning new providers when an in-scope resource matches.
- Swapping in a scope-registered provisioner changes offer sets deterministically with no core code edits.
- `PlanningReceipt.summarize()` distinguishes unresolved hard requirements from waived soft requirements in its diagnostics.

Following this plan keeps the reference implementation generic, auditable, and ready for domain-specific planners without architectural churn.
