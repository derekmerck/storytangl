# Scoped episode donation: characterization and ownership checkpoint

**Status:** #702 slice 2 implements referential owned-episode lowering for EAGER
stories. Scoped matching and Action projection are not implemented.
The broader offer/request convergence remains in
[Open Links](../../design/planning/AFFORDANCE_MODEL.md) and
[#255](https://github.com/derekmerck/storytangl/issues/255).

## From authoring to an ordinary action

The intended shape is: a nested authored episode belongs to a concept or
relationship; compilation records that declaration and its owner; normal template
materialization creates graph-owned episode state; provisioning considers the
declaration only where its owner/provider is legitimately in the receiver's scope;
the receiver's requirement binds the actual witnesses; Story projects an ordinary
Action to the shared destination. Owner, declaration, receiver, requirement/Role,
bound provider and destination are distinct references, even when some coincide.
Trigger data should pass through the same projection; choice is the default.

The tests in this slice prove a narrower existing path: sandbox gathers a Role's
provider from the receiver namespace, deduplicates aliases, and projects a normal
scheduled-event Action. A sibling outside that scope gets no donation; removing
the roles removes the offer without deleting the provider. JSON restoration and
continued traversal preserve those bindings. `Frame._run_planning_phase` derives
the immediate successor's context, and the witness confirms that successor's
provider does not leak to the current node. Separately, ordinary authored Actions
call one shared destination from two receivers; destination-history `once`
prevents the second call after the first returns, including after JSON restore.
Provider-sponsored sandbox Actions are currently refreshed during reprovisioning;
their UUID retention is not established by these tests.

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
that ancestry. The next design must specify which owner context is intentionally
available while keeping the receiving episode as the active cursor.

An `actors.aria.episodes.chat` declaration becomes the ordinary qualified
`aria.chat` scene and its block templates. It does not add a receiver Action,
become the default entry, or imply the owner participates in the scene. Explicit
Actions can traverse it using existing EAGER traversal and JSON restoration.
Frozen EAGER construction binds the reference; no general frozen donation
readiness is claimed. LAZY remains unsupported for this shape: in the tested
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

The next bounded implementation should settle scoped binding for one ordinary
receiver before replacing sandbox's specialized path. Entry wording and once lowering, invocation context, namespace
refresh after binding, and supported eager/lazy materialization modes remain open.
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
