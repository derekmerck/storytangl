`tangl.mechanics`
=================

`tangl.mechanics` is a _namespace_ package for **mechanic families**: reusable
consequence grammars, semantic bindings, and author-facing facets that extend
story-domain concepts or episodes without replacing the `tangl.story` / `tangl.vm`
contracts.

The top-level package organization stays broad and family-oriented:

- `games`
- `progression`
- `assembly`
- `demographics`
- `presence`
- `sandbox`
- `simulation`
- later: `credentials`, other world- or plugin-provided families

Within each family, the preferred design lens is:

- **Kernel**: pure deterministic rule logic
- **Domain**: vocabularies, YAML catalogs, semantic bindings
- **Runtime**: state, offers, intents, records, receipts
- **Render**: prose, journal, and media projection
- **Writeback**: explicit consequence application
- **Facade**: thin `HasX` author-facing mixins or helpers

See `TRANSACTION_OFFER_DESIGN.md` for the cross-family vocabulary that unifies
provisioning offers, association checks, asset transfers, shops, services, and
writeback receipts.

The first runtime helper for that vocabulary lives in `transaction.py`. It is
deliberately small: an ephemeral `TransactionOffer` validates, accepts, and
receipts a list of commitments while domain mechanics keep their own policy and
author-facing words.

## Review Lens

When reviewing or reviving a mechanic family, describe it with these four questions:

- **Shape**: what artifacts exist at rest?
- **Behavior**: what transitions or computations occur?
- **Attachment points**: where does it plug into compiler, VM, media, or service flow?
- **Appearance**: what does it project outward as?

This lens is likely useful beyond mechanics, but mechanics is the first place we
are using it systematically.

## Current Families

### Reference

- **Games**: the clearest current integrated family. It spans kernel, runtime,
  projection, and limited writeback via VM hooks and the `HasGame` facade.

### Foundation

- **Progression**: strong stat and task kernel/runtime surface, not yet a full
  story-capable mechanic family.
- **Assembly**: constrained slot-and-budget optimization kernel used by higher-level
  authored loadouts.
- **Transaction offers**: cross-family writeback helper for preflighted,
  multi-leg mutations such as shop purchases, service exchanges, asset movement,
  and component assignment. It is not a shop engine or inventory model by itself.
- **Demographics**: profile and naming facet, currently being modernized toward a
  cleaner v38-facing surface.
- **Presence / Wearable** and **Presence / Ornaments**: reusable presence/runtime
  primitives that feed future outfit and appearance flows.

### Redesign

- **Presence / Look**: strong intended purpose, but its current shape and
  attachment points should be cleaned up before extending it further. The first
  rescue pass now gives it a deterministic description surface and a structured
  media payload, but richer projection hooks are still pending.

### Incubating

- **Sandbox**: first-pass package surface now exists. It is understood as
  dynamic scene-location hubs plus time/schedule/presence vocabulary, built on
  ordinary `MenuBlock`, `Fanout`, `Action`, target availability, journal, ledger,
  and replay machinery rather than a separate traversal subsystem. See
  `sandbox/SANDBOX_DESIGN.md`.
- **Simulation**: small operational-simulation kernels that attach through
  ordinary mechanics and VM seams. The first proof is a deterministic queueing
  model that uses a mutable core `Registry` as a future-event list, `HasGame`
  for re-entrant actions, and normal journal fragments for observation.
- **Credentials**: expected to compose game kernels, asset collections, render, and
  writeback rather than porting the legacy package wholesale.

### Archive

- `scratch/mechanics` remains an idea archive and prior-art inventory. Mine it for
  concepts, tests, and examples, but do not promote code directly without
  rederiving it against v38 contracts.

## Support Criteria

A fully supported mechanic family should:

1. Declare which layers it implements and which are intentionally absent.
2. Be describable through the review lens above.
3. Keep randomness explicit and controllable.
4. Keep writeback explicit rather than hidden.
5. Keep projection separable from kernel and writeback.
6. Avoid dependencies on `scratch/` and on example-only internals.

## Notes

- Top-level families remain broad for now; `kernel/runtime/domain/render` is a
  conceptual organization before it is a filesystem organization.
- `scratch/mechanics/calvin_cards` is the clearest local exemplar of “same kernel,
  many semantic skins” and is worth mining for future design examples.
