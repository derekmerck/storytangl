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

## Mechanics as Pressure Systems

Mechanics should help an author avoid enumerating cross-product decision trees.
Worlds provide rules, populations, resources, authority, histories, consequences,
and presentation policy; scenarios narrow those inputs; mechanics derive available
interventions, costs, outcomes, and durable writeback. Later scenarios can consume
the resulting artifacts, relationships, capabilities, and memories as new context.

Correctness is deliberately multi-axis. A choice may be allowed, rules-correct,
evidentially justified, easy for the player, and harmful to someone else. Those facts
remain separate so authored worlds can create moral, institutional, personal, and
resource pressures without a universal morality function or a special-case branch for
every combination.

Families contribute different parts of that grammar: assembly exposes component state
to downstream mechanics; progression and badges accumulate durable change; sandbox
presence and schedules determine what is currently in scope; transactions move custody
and value; games and contests resolve bounded pressure; credentials, combat, racing,
and similar capstones compose several of these surfaces at once.

See `docs/src/design/story/MECHANICS_FAMILIES.md` for the full convergence model,
including world/scenario/encounter narrowing and the exemplar-decomposition records
used to treat demonstration worlds as conformance cases and representational probes.

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

- **Progression**: integrated stat, training, challenge, situational-effect, and
  durable growth foundation, exercised by *Coronate the Regent*.
- **Assembly**: owner-bound component, slot, connection, and budget foundation
  used by credentials, presence, and vehicle examples.
- **Transaction offers**: cross-family writeback helper for preflighted,
  multi-leg mutations such as shop purchases, service exchanges, asset movement,
  and component assignment. It is not a shop engine or inventory model by itself.
- **Demographics**: profile and naming facet, currently being modernized toward a
  cleaner v38-facing surface.
- **Presence / Wearable** and **Presence / Ornaments**: reusable presence/runtime
  primitives for outfit and appearance flows.
- **Presence / Look**: deterministic semantic appearance, recursive text
  rendering, and renderer-neutral portrait requests. Rich paperdoll composition
  remains a media/presence follow-up.
- **Simulation**: small operational-simulation kernels that attach through
  ordinary mechanics and VM seams. The first proof is a deterministic queueing
  model that uses a mutable core `Registry` as a future-event list, `HasGame`
  for re-entrant actions, and normal journal fragments for observation.

### Integrated Verticals

- **Sandbox**: location, fixture, asset, mob, schedule, visibility, story-info,
  and dynamic affordance surfaces exercised by *Adventure Sandbox Slice*. It
  remains ordinary Story/VM traversal, not a parallel subsystem.
- **Credentials**: the worked convergence capstone. Credential Gate and Hall
  Monitor compose assembly, games, transactions, Presence, text/media
  projection, custody, recurrence, response, and durable consequence.

### Archive

- `scratch/mechanics` remains an idea archive and prior-art inventory. Mine it for
  concepts, tests, and examples, but do not promote code directly without
  rederiving it against v38 contracts.

## Support Criteria

A fully supported mechanic family should:

1. Declare which family facets it implements and which are intentionally absent.
2. Be describable through the review lens above.
3. Keep randomness explicit and controllable.
4. Keep writeback explicit rather than hidden.
5. Keep projection separable from kernel and writeback.
6. Avoid dependencies on `scratch/` and on example-only internals.

## Notes

- Top-level families remain broad for now; the facet names above are review
  concepts, not engine layers or a required filesystem organization.
- `scratch/mechanics/calvin_cards` is the clearest local exemplar of “same kernel,
  many semantic skins” and is worth mining for future design examples.
