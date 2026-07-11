---
name: storytangl-feature
description: Plan, implement, review, or close one bounded StoryTangl feature slice using devref, architectural chokepoints, and constructor-form persistence checks. Use for substantial mechanics, VM, story, service, or cross-surface changes; do not use for trivial edits.
---

# StoryTangl Feature Slice

Run exactly one mode per task: `plan`, `implement`, `review`, or `close`.
Do not advance through multiple modes autonomously. Read the root and applicable
local `AGENTS.md` files plus the named design documents before editing.

## Local Environment Fallback

Prefer `poetry run`. If it fails only because Poetry cannot create or write its
virtualenv cache, do not install dependencies or treat that as a feature blocker.
Locate a pre-existing StoryTangl Python 3.13 venv, verify it imports `tangl`, then
run tools with explicit source paths:

```text
PYTHONPATH=engine/src:apps/cli/src:apps/renpy/src:apps/server/src \
  <verified-python> -m tangl.devref <command>
```

Do not hard-code a machine-specific venv path in committed docs. If no suitable
venv exists, planning may use targeted `rg` plus the named canonical files; report
the missing index rather than creating a new retrieval system.

If Git LFS prevents broad `git status`, use scoped `git diff -- <paths>` and
`git diff --check -- <paths>` for the current slice. Do not spend a planning task
repairing unrelated local Git/LFS environment state.

## Plan

1. Use `tangl-devref find` and `map` to identify canonical docs, code, tests,
   and related work. Use `pack` only for selected topics.
2. Write a compact feature contract using
   [feature-contract.md](references/feature-contract.md).
3. Name existing mechanisms to reuse, canonical chokepoints, non-goals, affected
   surfaces, acceptance checks, and any dependency that is not yet landed.
4. Stop for approval. Do not edit implementation code.

## Implement

Require an approved contract and one named milestone. Read only its selected
devref pack, local design docs, and code surface.

Before editing, state:

- capability needed;
- canonical chokepoint and reuse mechanism;
- expected files and validation;
- whether a new pathway is required.

Never create a parallel serializer, persistence route, dispatch system, registry,
factory, or lifecycle path without explicit contract authorization.

For graph-owned state, prove `unstructure()` / `structure()` through the owning
graph. `model_dump()` / `model_validate()` may inspect a Pydantic snapshot but
do not establish persistence correctness.

On an unexpected test failure, first state the failed design assumption. Check
the existing extension point and utilities before editing. Stop and report after
two failed corrections to the same cause, or when the correction needs a new
architectural pathway.

## Review

Compare the contract, actual diff, and selected canonical sources. Start with:

- layer-boundary and existing-mechanism reuse;
- graph/reference round trips and fresh-process singleton availability;
- setup/UPDATE versus PLANNING mutation boundaries;
- owner attachment after prior preparation or materialization;
- public, demo, widget, documentation, and test surfaces.

For PR review, use the actual PR base SHA for incremental CodeRabbit. Treat a
clean agent review as supplementary evidence, never as a substitute for a
targeted behavioral probe. Retrieve unresolved inline threads only; avoid
loading generated review walkthroughs or entire discussion dumps unless needed.

## Close

Run the contract's focused verification, inspect the diff, update a touched
design document's status, and record concise workflow observations in the
contract. Do not broaden closure into a new feature phase.

## Communication Economy

Use terse labeled status and diagnostic reports. Preserve exact APIs, commands,
errors, modality, and uncertainty. Do not compress canonical prose or load a
large historical thread when a fresh task can use the approved contract.
