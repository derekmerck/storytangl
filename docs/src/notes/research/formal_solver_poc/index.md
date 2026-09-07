# Formal solver integration proof of concept

```{admonition} Research status
:class: caution

This is a non-normative, externally authored proof of concept. It is preserved
as evidence for a possible analysis contract and optional solver backend; it
does not define current StoryTangl runtime behavior or establish Clingo as an
engine dependency.
```

This small Answer Set Programming (ASP) example explores two related uses of a
formal solver:

- offline authoring analysis, including bounded plan search, suspect-action
  survivability, cascade provenance, and simple producer/consumer checks; and
- an explicitly solver-owned deduction mechanic whose live hypotheses may be
  projected through ordinary StoryTangl game and journal surfaces.

The useful architectural idea is not the ASP syntax itself. It is a generated,
solver-independent analysis contract: typed state, operators, automatic
transitions, goals, analysis scope, stable source identifiers, and provenance.
A Clingo adapter could consume that contract, while the StoryTangl runtime
remains the semantic oracle used for differential validation.

## Included files

- {download}`engine.lp` — finite-horizon transition rules, triggers, goals, and
  action minimization.
- {download}`world.lp` — a compact apartment-management scenario with a
  deliberate ice-cream resource trap and an automatic character cascade.
- {download}`driver.py` — minimum-horizon search, bounded suspect-action
  survivability, provenance, and def-use reports.

The files are archived verbatim from the proposal. They are examples to inspect
and evolve, not installed test fixtures.

## What the example demonstrates

- Preconditions, add/delete effects, inertial state, linear resources, and
  one-shot automatic transitions can be represented compactly.
- The same model can support several author-facing questions without embedding
  those questions into the StoryTangl phase bus.
- A deliberately bad action can serve as a useful bounded counterexample.
- Stable mappings back to authored StoryTangl elements would be essential for
  actionable diagnostics.

## Limits of the evidence

- `UNSAT` through a chosen maximum horizon proves only that no plan exists
  within that bound unless a finite-state completeness bound is also
  established.
- The prefix-based trigger classification and syntactic def-use checks are
  intentionally simple and may report false positives.
- The model does not yet prove equivalence with StoryTangl's real settled
  choice semantics: redirects, provisioning, UPDATE effects, graph-owned game
  state, and persistence must be exercised through cloned `Ledger` runs.
- `ProjectedGraph` is an observational view of materialized topology, not a
  predictive state-transition graph.
- Player-facing categories should distinguish authored axioms, entailed facts,
  live hypotheses, and refuted hypotheses. Brave/cautious consequences are not
  automatically equivalent to genre-specific “blue” and “red” truth claims.
- Credentials keeps its canonical rules-correct `expected_disposition` separate
  from surfaced evidence. A solver may add an epistemic-support projection, but
  should not replace that correctness chokepoint.

## Architectural boundary for a future implementation

An authoring analyzer is observational: it emits diagnostics and witnesses, but
does not decide generic runtime choice availability. A solver-backed deduction
game is different: the solver may own that mechanic's hypothesis state, while
the mechanic still commits through the existing game handler, UPDATE, journal,
and persistence contracts. Any broader runtime use first needs differential
tests against ordinary `Ledger.resolve_choice()` transitions.

## Verified, 2026-09

The example was archived unverified because Clingo was not installed. It is now
an optional extra (`poetry install --extras solver`) and `driver.py` runs:

- **minimum horizon 15** for the apartment summit, 13 player moves and 3 forced;
- **`eat_icecream` proven fatal** — forcing it into the trace leaves the goal
  unreachable at every horizon up to 20;
- `mom` and `partner` reported cascade-bound, and two `known` facts flagged as
  offered but never consumed.

Bounded, not complete: UNSAT to horizon 20 is a statement about 20 moves.

`worlds/red_paperclip` emits this same content-pack vocabulary from its trade
graph (`python -m red_paperclip --asp GOAL`), which makes it a *generated*
second scenario next to this hand-written one — and its plan is played back
through an ordinary `Ledger` in `test_red_paperclip_world.py`, which is the
first instance of the differential validation this proposal asks for.
