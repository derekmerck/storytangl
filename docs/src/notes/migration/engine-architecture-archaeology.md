# Engine Architecture Archaeology

This note preserves selected design precedent from the retired
``scratch/legacy`` engine snapshots. Their removal is not a claim that every
idea was ported or exhausted. The initial cleanup summary covered architectural
convergence but under-documented documentation experiments, assets, actor
composition, and utilities. The inventory below repairs those omissions.
Git history remains the source for exact historical code.

## What the experiments established

### Explicit dispatch beat general plugin machinery

The v2 experiments used ``pluggy`` and then increasingly flexible MRO-driven
task pipelines. They demonstrated that a generic plugin manager made handler
priority and overlapping responsibility difficult to see. The durable result is
the current explicit ``BehaviorRegistry`` and phase-hook vocabulary: one
dispatch mechanism, deterministic ordering, and world/domain authorities that
state where behavior comes from.

### Constructor form beat automorphic construction

``Automorphic``, ``Templated``, and ``SmartNew`` explored data-driven
self-casting, inferred subclasses, and default/template lookup during object
creation. These were clever demonstrations of how much Python could infer, but
they hid ownership and made persistence shape difficult to reason about. The
current explicit ``unstructure()`` / ``structure()`` contract and
``EntityTemplate.materialize()`` path retain polymorphic construction without
the inference pipeline.

This is also a negative precedent: embedded constructor-form values opt in;
graph entities normally persist by reference; field names and defaults do not
silently determine object types.

### Context services converged into a phase context

The v3.3-v3.4 capability/service experiments represented context gathering,
predicates, effects, rendering, and provisioning as injectable entity services.
They clarified the operations the engine needs, but made the execution model
more abstract than the work itself. The useful vocabulary survived as typed
phase hooks operating on one ``PhaseCtx`` and composing through the behavior
registry.

### Domains separated scope from engine layers

The v3.7 domain and scope work established two lasting ideas: structural
ancestry contributes local namespace, and a world may contribute policy and
behavior without importing that policy upward into core. Earlier proposals
cached edge projections inside domain variables and refreshed them after
planning/update. The current design instead derives scoped role/setting values
from live graph state, avoiding a second mutable projection and its cache
invalidation lifecycle.

### Determinism and receipts survived; mutation watchers did not

The v3.7 VM made phase order, handler ordering, receipts, replay, and a separate
journal explicit. Its watched-object event stream was useful instrumentation,
but proxying every mutation proved to be the wrong persistence boundary. The
current ledger, constructor-form snapshots, graph diffs, and receipt streams
preserve deterministic/auditable execution without making observable proxy
behavior part of every domain object.

## Documentation approaches and topic foci

Historical paths in this inventory are relative to `scratch/legacy/` at the
pre-removal commit `20afda632f896adba5b982a670f77b47114c3563`.
The [historical documentation tree](https://github.com/derekmerck/storytangl/tree/20afda632f896adba5b982a670f77b47114c3563/scratch/legacy/docs)
is browsable without restoring it. These are glosses of representative source
documents and the directory inventory, not a line-by-line certification of
every old proposal.

| Collection | Documentation approach | Ideas worth remembering |
| --- | --- | --- |
| `docs/docs_v25/` | MyST/Sphinx API pages organized by Core, Story, World, Games, and service API; separate story/node lifecycle walkthroughs. | The engine as an authoring system, not just a graph library: casting, fungible wallets versus discrete inventories, games inside challenge blocks, narrator/illustrator/speaker roles. |
| `docs/docs_v25/ge_logic.md` | Cross-cutting system outline from story generation through scripting and clients. | STRIPS-like preconditions/effects; language and illustration intermediate formats; author-facing qualitative quantities; connectivity, completeness, and finishability checks. These are historical intentions, not evidence that every tool existed. |
| `docs/docs_v28/` | Explicit content-creator versus backend-developer guides, mostly reStructuredText/autodoc. | Single-file and directory-based scripts normalize to one ingestion form; an Obsidian notebook lane was marked in progress. World/static versus story/dynamic media and forge extension points were central concerns. Pluggy hooks were the extension vocabulary then. |
| `docs/docs_v3x/` | Parallel Markdown/RST API-reference and developer-overview attempts, with core concepts, mixins, handlers, and hooks. | Explaining authors, extension developers, client developers, and players separately. The overview mixes implemented features and aspirations; do not read its localization/media/scalability claims as a parity checklist. |
| `docs/overviews/overview-ext/`, `story_philosophy.md` | Essay-style explanation of the Abstract Narrative Graph and its philosophical motivations. | Fabula / episodic process / syuzhet; latent possibility versus realized narrative; different story/discourse clocks; journal projection; philosophy as explanatory metaphor, not a runtime requirement. |
| `docs/overviews/project_overview32.md`, `project_overview33.md`, `notes_v34.md`, `project_overview37a.md` | Versioned architecture sketches and implementation-status narratives. | Shift from task/handler pipelines and capability services toward explicit VM phases, provisioning, scoped domains, receipts, determinism, and portability. The v37 overview explicitly labels several pieces as skeletons or previews. |
| `docs/overviews/mvp_action_items.md`, `planning_phase_roadmap.md`, `ledger_persistence_plan.rst` | Implementation roadmaps with proposed APIs and tests. | Separating script materialization, provider selection, and service/ledger persistence. Preserve problem framing; do not revive their old managers and watcher plumbing as parallel authorities. |

`story_philosophy.md` also contains a useful **unverified idea bank**: narrative
velocity, tension from unresolved dependencies, emotional arcs, genre contracts,
dramatic irony, gated reveals, foreshadowing, and backward resource-use checks
(Chekhov's gun) alongside forward requirement satisfaction. These are not all
absorbed merely because today's engine has provisioning and a journal. Revisit
them when a narrative-analysis or showcase consumer needs one; keep them out of
the current architecture's implemented-feature claims.

## Assets, trade, and re-attachable associations

Historical sources:

- `story/story-211/asset/fungible.py` and `tradeable.py`;
- `story/story-23/asset/commodity.py`, `commodity2.py`, and `wallet.py`;
- `story/story-23/scene/market.py`;
- `core/core-32/graph_handlers/associating.py` and its
  `core-32-tests/test_association.py`;
- `story/story_tests/asset/` and `story/story_tests/test_fungible.py` preserve
  additional examples to consult during a dedicated asset review.

The durable distinctions were:

1. **Fungible quantities versus individual things.** A wallet counts catalog
   kinds; an individual tradeable retains identity when moved between holders.
2. **Valuation versus transfer.** Commodity value, currency, discount, and
   aggregate utility are policy over an exchange, not the ownership mechanism.
   `commodity2.py` explicitly explored tradeability as a protocol rather than
   requiring everything saleable to be one asset subclass.
3. **Bilateral permission.** Giving/releasing and receiving/accepting can each
   reject; willingness to exchange is distinct from mechanical ability.
4. **Mutable association.** Parent/child and peer links have inverse roles and
   both endpoints participate in association/disassociation checks and hooks.
   Re-attachment matters beyond inventory: roles, equipment, and other bindings
   can change without replacing the participating entities.
5. **Provider policy.** The market spike explored stock refresh, relationship/
   level unlocks, and policy effects. Its purchase-cost and stock-registration
   TODOs mean it was not a completed market implementation.

Current overlap is real, but bounded. `story/concepts/asset/` contains
`CountableAsset`, `AssetWallet`, `HasAssets`, and `AssetTransactionManager`.
`mechanics/transaction.py` supplies ephemeral offers, bilateral count transfers,
discrete asset moves, catalog creation, and ordered rollback-capable commitments.
The asset and transaction focused suites passed **50 tests** in this audit.
That does not certify all inventory persistence or all historical trade policy.

The [asset design](https://github.com/derekmerck/storytangl/blob/a0f473394ef2e68320fcf0e9b7905b8166a1182f/engine/src/tangl/story/concepts/asset/ASSET_DESIGN.md)
explicitly defers relationship-backed ownership. Current holder maps and transaction adapters are not
proof that general re-attachment/preflight hooks landed. The
`engine/src/tangl/mechanics/TRANSACTION_OFFER_DESIGN.md` already retains bilateral
association as prior art and defers general graph-link commitments. Aggregate
valuation, bargaining/willingness policy, and market restocking are separate
consumer questions, not implied by an atomic transfer helper.

Negative precedent: the old `AssetWallet.transact()` performs send then receive
without rollback; `ProxyWallet.__exit__()` writes back even after an exception.
Preserve the vocabulary and examples, not their mutation protocol.

## Mind/body composition and identity-swapping demos

`story/story-23/actor/mind.py`, `body.py`, `person.py`, and `actor.py` preserve
two separable sets of character traits. Mind held names, mental traits, fluency,
and preferences; body held physical capability, appearance, age, and ornaments.
`Person.communicates()` combined mental fluency with bodily voice capability.
`actor.py` marked selected fields with `decompose: body` metadata.

This is useful precedent for a **world-local mind-swap or embodiment demo**,
not evidence of a current mechanic. The snapshot imports `DecomposableMixin`
but contains no matching implementation in the inspected legacy story/core
trees, so these files do not prove a working swap pipeline even historically.
Current Look/demographic/stat facets are not an equivalent identity-transfer
contract.

For a future demo, first decide what follows the mind (memory, learned skill,
preferences), the body (physical capability, appearance, worn items), or the
social identity (name, reputation, relationships, credentials). Then demonstrate
one explicit swap during UPDATE, namespace/journal consequences, and graph
constructor-form round-trip. Do not promote the old setting-specific anatomy,
valuation assumptions, or automatic field decomposition into core.

## Utility experiments: salvage inventory

The initial deletion did not provide this inventory. This pass read the small
utility implementations, inspected larger model/dispatch helpers, and surveyed
the paired test names with focused reads of chain-singleton and overlap-picking
tests. Historical tests are evidence of intended behavior, not current passing
tests; they were not run against v38.

### Especially useful precedents

- **`utils/chain_singleton.py` + `utils-tests/test_chain_singleton.py`:** named
  dictionary singletons with an `extends` chain and item/attribute fallback.
  The A → B → C test captures cascading inherited values. This preserves the
  namespace/defaults idea, but does not establish its former production callers.
  Current `PhaseCtx.get_ns()` returns a scoped `ChainMap`; current
  `InstanceInheritance` copies defaults at construction. Neither is the same as
  live multi-parent dictionary inheritance. The old fallback also raises on a
  missing key in the first parent before trying later parents, skips `None`, and
  has no cycle handling. Retain the gloss; do not revive a second namespace system.
- **`utils/pick_n.py` + `utils-tests/test_pick_n.py`:** distinct representatives
  from overlapping candidate pools, motivated by casting several roles at once.
  It ranks candidates by rarity and greedily assigns them. This is an important
  problem statement, not a complete matching algorithm: it has no backtracking.
  Current per-requirement offer ranking is not proof of joint distinct-role
  assignment. Preserve for a constrained-casting/planning review, with an
  explicit no-reuse requirement before proposing a solver.
- **`utils/bookmarked_list.py` + its tests:** typed/named section markers,
  negative-index lookup, containing-section lookup, and early stops at enclosing
  section boundaries. Current `Ledger.find_marker()` and `get_marked_slice()`
  cover much of this, including stop-marker types. Keep as journal-query
  precedent; compare boundary semantics before claiming exact parity.
- **`utils/log_int.py` + its tests:** logarithmic arithmetic with authored
  qualitative levels; combining two middle quantities can produce a higher
  tier. This is not interchangeable with a linearly accumulated float merely
  because both display a quantized label. Carry into the separate progression
  review alongside #112; do not silently fold it into current stat math. The
  author's clarified motivation was doubling power per rank: two rank-n tokens
  equal one rank-(n+1) token. A temporary matchup brevet changes effective rank,
  not permanent token identity. Log scaling is optional for the token games
  below; plain integer or other power scales can serve the same game structure.
- **`utils/recursive_deep_merging.py`, `deep_merge.py`, `glob2dict.py`:** deep
  fallback lookup, eager `$name` substitution, list concatenation/positional
  dictionary merging, and `_key` override conventions. These capture old
  authoring semantics, not a reason to reintroduce implicit runtime merging.
  Revisit only for a concrete compiler/codec compatibility requirement.

### Bag, siege, and winding-RPS spikes

The dedicated game-design pass these were preserved for has happened. Bag and
siege are now implemented and their scratch sources deleted; the winding-RPS
geometric experiment is not, and remains under
`scratch/mechanics/games/token_games/winding_rps/`.

- `bag_rps.py` and `siege_rps.py` **landed** as `BagRpsGame` and `SiegeRpsGame`
  over the shared `AggregateForceGame` kernel. Two of the open questions below
  are answered there: dominant affiliation is decided by weighted value with an
  explicit alphabetical tie-break rather than incidental ordering, and the
  survivor return/withdraw cycle is real — commitment transfers reserve into an
  active pool and every committed token is routed afterwards by an explicit
  disposition (conserve, retire, decimate, or cede). See
  `GAME_MECHANICS_DESIGN.md`.
- `winding_rps/wind_rps.py`: an alternative to reducing the whole force to its
  dominant affiliation. It compares normalized power distributions under cyclic
  rotation, converts distance into an effective-power multiplier, and randomly
  decimates both sides. It also experiments with a probabilistic final casualty
  when remaining damage is less than one token's power.
- `winding_rps/sig.py`: named stone/iron/glass affiliations and `ADAPTIVE`
  units. `Force.winding_dist()` delegates to `Hand.adaptive_winding_dist()`,
  which temporarily tries each affiliation for each unassigned unit, greedily
  retains the best distance, then resets the units to unassigned. This is a
  concrete **matchup-local joker** experiment, not merely a prose suggestion.

The author also recalls unique adaptive tokens being lost last. Preserve those
as two independent policies: **adaptive affiliation** and **casualty priority**.
Both are still open. Casualty *policy* is now a named registry
(`casualty_policies`, with count- and power-denominated members), but casualty
*targeting* — which tokens die first — remains undecided, because a bag of
counts has no per-unit identity to prefer. Adaptive affiliation has no
implementation at all. Likewise,
the old count-based bags do not prove durable identity for individual heroes.

The design payoff is drafting a smaller counter-force against a known or hinted
opponent, with losses persisting beyond the comparison. Outstanding choices
include mixed-affiliation ties, matchup bonus scope, both sides having jokers,
casualty allocation, and survivor return. Do not confuse these policy questions
with choosing logarithmic versus linear power. The token-game test module is
skipped, and these incompatible snapshots were not executed in this audit.

The author recalls the default unit vocabulary as **brute** (rock), **sharp**
(scissors), and **fast** (paper). Preserve this as a world-facing categorical
skin, not a mandatory engine enum. The geometric approach was an attempt to
extend cyclic dominance to mixed forces through barycentric weights and winding
rather than only a lookup matrix. Reported degeneracies include balanced forces
becoming undominatable and unstable cross-product comparisons for nearly equal
weightings. These are historical design observations, not newly reproduced
results: the inspected `wind_rps.py` uses rotated-vector distance, not a cross
product. A future game-design pass should specify balanced-force tradeoffs and
near-tie neutrality before selecting a geometric or matrix-based rule.

### Remaining utility families

| Sources under `utils/` | Salvage decision |
| --- | --- |
| `alias_dict.py`, `bunch.py`, `set_dict.py` | Alias refresh, unique-result lookup, case aliases, enum-keyed alternatives. Current Registry/Selector and typed namespaces are the primary surfaces. Alias ambiguity and deterministic alternative selection remain useful test questions; the old AliasDict is not truly many-to-many despite its docstring. |
| `dyn_enum.py`, `enum_utils.py` | Data-authored vocabularies and alias parsing. Current Singleton catalogs and EnumPlusMixin cover related needs. Do not silently restore fuzzy substring matching, clamping, or dynamic enum metaclasses. |
| `base_model_plus.py`, `attrs_tricks.py`, `as_eid.py` | Field metadata, copy/reset helpers, parent inference, and reference projection. Current core bases and constructor form own these responsibilities; inferred parenting and mutation-during-serialization are negative precedents. |
| `func_info.py`, `compare_ftypes.py`, `is_method_in_mro.py`, `inheritance_aware.py`, `property_hints.py` | Callable binding/signature inference and subclass/property inspection. Retain as explanation of the earlier inference-heavy dispatch/construction approach, not helpers to reintroduce beneath explicit Behavior/typed interfaces. |
| `ansi.py`, `deep_md.py`, `mag.py`, `mlconjug3.py` | Terminal rendering, recursive Markdown rendering, compact numeric-unit formatting, and alternate conjugation lookup. Renderer/language-boundary conveniences; no blanket parity claim. `mag` is a small reusable presentation idea; the old conjugation adapter labels its source non-authoritative. |
| `generate_frontend_ts_spec.py` | Backend-to-client schema drift prevention is valuable; the old script explicitly says its generator is broken/obsolete. Preserve the goal, not its dependency patches. |
| `file_check_values.py`, `hash_dir.py` | File freshness and world-source cache invalidation. Keep historical intent only; hashing decisions remain in the separate hashing workstream. |
| `topological_sort.py`, `flatten_list.py`, `make_repr.py`, `summary_repr.py`, `yaml_tricks.py` | Routine dependency ordering, flattening, debug formatting, and YAML sequence splicing. No reason found to restore these utilities. Sequence-splicing syntax needs a concrete authoring consumer before adoption. |

### Bounded follow-up handoff

1. Leave the removed trees in Git history; this inventory is not authorization
   to recreate or port them wholesale. Do not delete additional topical scratch.
2. For transaction work, start at current asset/transaction designs and tests.
   Compare bilateral ownership/re-attachment and pricing policy separately;
   do not build another wallet or transaction framework.
3. Carry logarithmic quantities into the independent #112 progression audit.
   Keep the constrained-casting example and mind/body demo as unported ideas
   until a dedicated design pass chooses their semantics.
4. For any promoted idea, add a minimal behavioral example, identify the current
   owning surface, and prove integration/persistence where relevant. Only then
   describe the historical capability as absorbed. Helper tests alone are not
   end-to-end proof, as the ornament-coverage audit demonstrated.

## Reading the history

The v38 parity matrix records which legacy behavioral tests were ported,
adapted, moved, or intentionally retired. Current contracts live in
``ARCHITECTURE.md`` and the nearest ``*_DESIGN.md`` file. For an exact old
implementation, inspect the repository commit before the hygiene removal
rather than restoring a second source tree beside the active engine:

```sh
git show 20afda632f896adba5b982a670f77b47114c3563:scratch/legacy/utils/chain_singleton.py
git ls-tree -r --name-only 20afda632f896adba5b982a670f77b47114c3563 scratch/legacy/docs
```
