# Scoped episode donation: characterization and ownership checkpoint

**Status:** #706, #707 and #709 are merged characterization, reference-ownership
and source-bookkeeping foundations. #710 adds retained ordinary call Actions
for scoped owned scenes in EAGER, mutable stories. LAZY/JIT projection and
invocation-context enrichment remain follow-ups. #717 extends the
shared owned-Scene path to sandbox locations and removes their provider callback.
Scene calls and location-sponsored Actions now share template-backed scoped
reconciliation in EAGER mutable stories. Other sponsor families remain pending.
The Role-owned witness supports a bound scene Role as a distinct offer owner;
it does not add automatic recasting or a general unbound-Role offer policy.
The paired Crossroads examples in `worlds/crossroads_receiver` and
`worlds/crossroads_sponsor` exercise this path and explicit receiver calls
through local Service, JSON and the CLI; they do not establish REST, visual
parity or general client conformance.
The broader offer/request convergence remains in
[Open Links](../../design/planning/AFFORDANCE_MODEL.md) and
[#255](https://github.com/derekmerck/storytangl/issues/255).

The [assembly, gating and walking contract](../../design/planning/AFFORDANCE_MODEL.md#assembly-gating-and-walking-convergence-contract)
governs that convergence. It separates declaration templates from executable Actions,
relationship inputs from derived links, continuing identity from parameter freshness,
and readiness from traversal phase entry. Scoped Action offers embed an Action
template in constructor form; executable Actions are materialized at receiving
sites. #560 separately settles what completes or abandons an open call.

An Action successor of `current` means its own receiving site. To refer to a
block literally named `current`, use its qualified path, such as `inn.current`.
The same rule applies to ordinary and scoped Actions.

## From authoring to an ordinary action

An affordance's `source_ids` is an ordered record of attachment sites, not
executable adjacency or proof of current eligibility. Its existing binary
predecessor and successor retain their graph-index semantics. A caller checks
`source_requirement` against the actual site or ancestor in that receiver's
context; the latest recorded source does not select another receiver's context.
Unchanged planning must not reorder the record. Structural scope loss removes a
local projection, while a matching but unavailable offer retains its projection
and uses ordinary availability and disclosure. Story revalidates these conditions
on selection. Recording sites itself performs none of that projection or live
policy evaluation.

An Action used by an active call remains in the graph as its return bookmark
when the offer detaches. It is no longer disclosed or selectable; subsequent
reconciliation removes it after the call stack releases it.

An owned scene can declare `offer: {source_requirement: {has_tags: [tavern]},
once: true}`. EAGER materialization binds one affordance from its owner to the
scene. Provisioning discovers owners from the receiving namespace and bound
roles/settings, matches the receiver or one actual ancestor, and reconciles
ordinary Actions without cloning the scene. Offer and availability-capable sponsor
predicates and Action-local guards use the actual receiver's namespace; author
receiver-relative call conditions in `SceneOffer.availability`. Scene admission
and entry-Block readiness use their ordinary destination namespaces. In the
regression witness, opposing `ready` values at receiver, Scene and entry do not
shadow the destination's own gates; disclosure, preview and selection agree.
A scene's owner does not become its ancestor.
The shared affordance uses the existing predicate availability mixin; it does
not add a separate lock mechanism or recursively inherit parent availability.

An explicit owned Scene may name an ordinary scene Role declaration:

```yaml
scenes:
  inn:
    tags: [tavern]
    roles:
      bard: {actor_ref: aria}
    blocks:
      hearth: {content: By the hearth.}
  conversation:
    owner_ref: inn.roles.bard
    offer: {source_requirement: {has_tags: [tavern]}, once: true}
    blocks:
      message: {content: The road is open.}
```

The declaring Role is normally wired first; `Scene.owner_id` then references
that existing Role edge. Its provider is a separate Actor reference. Discovery
uses the receiver's scoped Role symbols, so the same Actor in an unrelated
Role does not carry the relationship's offer there. A controlled compatible
provider replacement keeps the owner, offer and retained Actions while ordinary
Role grants and aliases follow the new binding. A removed owning Role cannot
authorize an Action from its historical site record. Actor and Location owners
continue to use their existing exact template references. No caller cast is
implicitly added to the detached conversation's namespace.

The intended shape is: a nested authored episode belongs to a concept or
relationship; compilation records that declaration and its owner; normal template
materialization creates graph-owned episode state; provisioning considers the
declaration only where its owner/provider is legitimately in the receiver's scope;
the receiver requirement matches an actual site or ancestor; Story projects an ordinary
Action to the shared destination. Owner, declaration, receiver, requirement/Role,
bound provider and destination are distinct references, even when some coincide.
Trigger data should pass through the same projection; choice is the default.

The shared offer path covers both ordinary Blocks and sandbox locations. Its
witness deduplicates two Role bindings to one Actor, excludes a sibling outside
scope, retains the Action across replanning and temporary availability changes,
and removes it after structural exposure is lost. Constructor-form JSON restore
preserves the bindings and continued call/return. Frame planning uses the
immediate successor's own scope. Destination-history `once` is witnessed across
ordinary receivers and JSON restore.

## Ownership and lowering recommendation

An actor's `episodes` mapping lowers through normal scene/block templates to
graph-owned scenes; an explicit scene `owner_ref` uses the same representation.
EAGER materialization resolves the exact owner to `owner_id`; `Scene.owner` reads
the live graph object. This preserves literal nested authoring as an ownership
declaration without treating the owner as a namespace ancestor.
`StoryCompiler.compile` currently compiles actor declarations separately from
scene/block children; `Actor` is a plain `Node`, `Role` a `Dependency`, and
`GraphItem.parent` recognizes `HierarchicalNode` membership. Thus putting an
episode under an actor in source does not make the actor its namespace ancestor.
Making Actor hierarchical would alter a
Core ownership/ancestry contract; a reference alone also must not silently claim
that ancestry. Richer explicit invocation-context enrichment remains deferred.

An `actors.aria.episodes.chat` declaration becomes the ordinary qualified
`aria.chat` scene and its block templates. Ownership alone does not add a
receiver Action, make it the default entry, or imply the owner participates in
the scene. An explicit offer supplies the additional projection policy. Explicit
Actions can traverse it using existing EAGER traversal and JSON restoration.
Frozen EAGER setup reconciles scoped Actions for all realized Blocks after entry
selection and story-ready hooks. Unchanged bindings retain their IDs and live
gates remain live; a newly required or changed binding is refused at runtime.
Targets not already realized remain outside this readiness slice. LAZY remains
unsupported for this shape: in the tested
actor-qualified destination, initial setup left the episode unmaterialized and
selecting its unresolved Action failed validation. It is not eagerly expanded to
hide that gap.

Candidate lowering chokepoints are the existing compiler/template grouping and
`EntityTemplate.materialize`/factory attachment, graph-owned reference restoration,
`PhaseCtx.get_ns`/`derive`, and `Resolver`/provisioner matching before Story Action
projection. Ordinary receiver-owned requirements and scoped sponsor offers should
share those binding and projection paths, retaining the actual requirement and
provider witnesses. `FindProvisioner.get_affordance_offers` can enumerate matching
affordances in supplied groups, but has no production caller in this baseline; it
is not evidence that reverse discovery is already wired. Do not add a global graph
donor scan, Actor-only projector, second dispatcher, mandatory contributor methods,
or a generic persistent match record by default.

The ordinary receiver path uses Scene action wording and explicitly authored
destination-history once. Invocation context enrichment and lazy materialization
remain open. Sandbox locations also receive shared Actor-owned Scene offers;
other sandbox scheduled-event families retain their own projection paths.
Keep normal one-step-ahead planning and the existing justified JIT path: descending
eligible contributions is not expansion of future game trees. Scheduling,
preemption, per-cause instances, general capacity/arbitration, alternative casting,
BoP rules and full recasting remain separate follow-ups.

Follow-on consumers also distinguish the grant beneficiary from owner, provider
and receiver. Deliberately exposed wallet membership or a declared relationship
chain may supply scope; neither implies unrestricted graph traversal or namespace
flattening. `HasAssets` and [asset ownership](concepts/asset/ASSET_DESIGN.md)
are existing custody precedents, not an implemented donation path. Once a source
qualifies, a live willingness refusal may retain an unavailable ordinary Action
with its existing Blocker and disclosure, rather than erasing the binding.

Live bindings and committed historical evidence have different lifetimes: later
consumers may need selection-time cast and cause after recasting, without recording
tentative matches. Match inputs such as accused plus episode are not a universal
instance key; repeated causes may differ. Viability preview may consider
template-creatable providers without creating or sampling them during a read.
Eligibility may use computed current namespace/world values at semantic evaluation
boundaries, not GUI ticks. Custody traversal, proxy entitlements, historical
registries, generation and claims remain outside this slice.
