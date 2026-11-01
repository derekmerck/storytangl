# Geopolitical Constellations: a Balance of Power pastiche

**Stage:** selected world-design / implementation proposal; not yet an executable world.  
**Implementation:** [#654 — Crawford-inspired geopolitical incidents (first vertical)](https://github.com/derekmerck/storytangl/issues/654).  
**Purpose:** bounded world-and-mechanics demonstration; a semantic port of Crawford-style geopolitical interactions into StoryTangl.  
**Reference:** Chris Crawford, *Balance of Power* (1985), and *Balance of Power: International Politics as the Ultimate Global Game* (1986).  
**Research lineage:** [showcase portfolio #395](https://github.com/derekmerck/storytangl/issues/395), [scoped concept projection #255](https://github.com/derekmerck/storytangl/issues/255), [mechanics convergence #332](https://github.com/derekmerck/storytangl/issues/332), and the separately parked [Project Deikto #643](https://github.com/derekmerck/storytangl/issues/643).

## Premise and experiential invariant

Play one of two Cold War superpowers in a changing international system. Nations have resources, political alignments, governments, opposition, and geographic relationships. Foreign aid, support for insurgencies, destabilization, and diplomatic challenges have consequential effects beyond the immediate choice. The other superpower can object, escalate, concede, or take its own initiatives; weaker regimes can change; the next international opportunity emerges from the altered world.

**The characteristic Balance of Power experience is a chain of indirect consequences, not an authored sequence of international incidents.** An intervention affects political stability and relationships; those conditions influence the opponent's response, possible crisis, and subsequent interventions. A text/CLI transcript and semantic journal are sufficient to demonstrate this before a map client or polished narrative.

This is a **pastiche and semantic port**, not a reconstruction of the original executable. Crawford's processes and qualitative dependencies are the specification to translate; exact 16-bit arithmetic, the original country count, historical numerical parameters, scoring, GUI, and every simulation formula are not required. Record approximations and departures rather than claiming numerical fidelity.

The near-term question is whether a small amount of world-specific code, expressed in existing StoryTangl vocabulary, yields *recognizably similar causal behavior*. The broader 90%-of-the-narrative-with-10%-of-the-domain-code intuition is a research hypothesis, not a performance claim.

**Direction of travel.** This world is an incremental step toward a general *concept constellation with emergent choices* framework, in the line of Crawford's later Erasmatron and Storytron work: actors bound into roles around a cause, with available verbs and other actors' reactions emerging from state rather than from authored branches. Balance of Power is the starting point because its vocabulary is precisely bounded (a handful of policies, one crisis procedure, three world processes) and fully documented. Choices made here should not foreclose that generalization, but the framework is extracted from this and later consumers, not designed ahead of them.

## Crawford-ese to StoryTangl-ese

| Crawford concept/process | Proposed StoryTangl representation | Ownership |
| --- | --- | --- |
| Superpower or minor country | Persistent Nation concept/actor, role eligibility, relationships, and country state | World data and policies |
| Government and insurgents | Governing-power and opposition-power occupants of Nation assembly slots | World concepts/roles |
| Aid, soldiers, weapons, money | Resource definitions and wallet quantities where they are truly fungible | Existing asset machinery; world units |
| Population, geography, proximity, strategic value | Nation/region state and semantic graph relationships | World data |
| Diplomatic relationship, treaty, alignment | Persistent relationships/commitments and associated state | World model |
| Intervention, destabilization, treaty/policy change | Scoped affordances and normal Actions/effects | Domain handlers on existing VM |
| Insurgency, coup, Finlandization | World-update rules and possible incident/opportunity triggers | Domain-specific behavior |
| Crisis, challenge, escalation, retreat | Re-entrant GeopoliticalIncident episode with participant bindings, hosting an escalation ladder (CrisisLevel 9 → 1; back down or escalate) | Incident: world/story; ladder: crisis-specific game logic first, a reusable `mechanics/games` kernel if extraction is earned |
| Outrage, Hurt, bluffing, anticipation | Opponent strategy and per-policy Hurt functions over world state | World rules module |
| Adventurousness, Pugnacity | Per-principal state carried across crises: boldness record, and the momentum a crisis winner gains that intimidates the loser next time | World rules module |
| Prestige | Projection over nations' regard for each principal, weighted by military strength; not a wallet balance | World rules module |
| Computer-controlled opposing superpower | Deterministic actor policy choosing from available Actions | World behavior; not a second game engine |
| Annual/periodic world updates | Explicit world-tick transitions | World scene and domain handlers |
| Map and reports | Presentation of the same state, choices, and journal receipts | Client projection |

This is the *shell + spikes* shape described in the [composite game loops note](https://github.com/derekmerck/storytangl/blob/main/engine/src/tangl/mechanics/games/COMPOSITE_GAME_LOOPS_DESIGN.md): the re-entrant world scene is the shell (policies, annual processes, prestige), and the crisis is the spike (a short contest whose outcome feeds back into the shell).

Crawford's core processes are insurgency, coups, Finlandization/coerced alignment, and diplomatic crises. We can start with a much smaller subset and add the others after the first interaction works. A natural disaster creating rival relief and intervention opportunities is an attractive **later StoryTangl extension**, not a claimed feature of Crawford's original implementation. Likewise, the priest-versus-fruit-companies moral dilemma discussed in brainstorming is a useful design inspiration, **not an established Balance of Power scenario**.

## Proposed concept vocabulary

**Nation** is a persistent geopolitical actor-like concept: identity, population, economy, territorial/proximity facts, alignment and treaty relationships, and perhaps a small number of scoped affordance providers. It can satisfy different Participant role requirements by capabilities, not solely by a nominal major/minor class.

**PoliticalPower** is a durable actor-like concept or token representing a governing regime or organized opposition, with its own resources, policy disposition, and history. A Nation can have **governing_power** and **opposition_power** assembly/role slots. A coup or revolution changes the slot occupancy, not the Nation's identity. The distinction between a regime and its individual leader is *possible* but unnecessary for this proof.

**Participant** is a role contract in an incident: challenger, respondent, contested state, beneficiary, sponsor, or other incident-specific participant. Its occupant need not have a fixed object shape; it must satisfy the applicable requirement. The first implementation can use current Role/Selector/dependency facilities. Avoid a new universal political type hierarchy.

**Resources:** money, arms, or force counts may use CountableAsset/AssetWallet/HasAssets when the semantics are fungible and transactional. Wallets can also hold discrete members (loose tokens or other nodes) alongside fungible quantities, so an individually identified resource (a named military mission, a specific weapons system, an embassy) can sit in a wallet without needing an assembly slot. Population, geographic control, approval, and legitimacy are ordinarily state variables, not inventory. Decide whether soldiers are a count, asset, or derived military-strength quantity according to the rule being translated. Government and opposition wallets should not silently become the same wallet, nor should government-held funds imply ownership of all national resources.

*Later refinement, not part of the simple framework:* each nation can hold three resource pools: **national** (stays with the Nation through any change of regime: the police are still the police), **incumbent-bound**, and **opposition-bound**. When the balance of power shifts, some fraction of the incumbent and opposition pools trade places, so a coup captures specific resources rather than the whole country. The first slices may treat national resources as a single state block; nothing in them should assume that a regime change moves every resource.

A **principal** can sponsor great-power policies and diplomatic challenges; a **minor** is usually the affected party and may have its own responses, political updates, and limited actions. Start with USA and USSR as two configured principals and a few minors. Avoid encoding 'exactly two superpowers' as an engine invariant.

Illustrative authoring shape (not current schema):

~~~yaml
nations:
  nicaragua:
    classification: minor
    government: sandinista_government
    opposition: contra_opposition
    relations:
      usa: { affinity: -3, proximity: near }
      ussr: { affinity: 3, alignment: supportive }
political_powers:
  sandinista_government:
    wallet: { funding: 8, arms: 5 }
  contra_opposition:
    wallet: { funding: 3, arms: 2 }
~~~

These illustrative values are fictional testing fixtures, not historical measurements.

## GeopoliticalIncident: the first concrete constellation

A GeopoliticalIncident is a **persistent, role-bound Episode** whose configuration contributes choices and mutates shared state through ordinary VM handlers. Start with this concrete class/configuration; only extract a ConceptConstellationMixin after another consumer reveals what is genuinely common.

For example:

~~~text
GeopoliticalIncident #42
  type: diplomatic_challenge
  challenger -> USA
  respondent -> USSR
  contested_state -> Nicaragua
  contested_policy -> SovietMilitaryAid #19
  local state: challenge_level, pending_response, lifecycle
~~~

The *contested state* binds to the Nation, not necessarily its current governing power. If government changes, the Nation and incident can persist; eligibility and available decisions are recomputed in the current scoped namespace.

Keep three semantics distinct:

1. **Existential requirements:** enough appropriate participants, cause/policy, and context exist to instantiate the incident.
2. **Action availability:** mutable guards decide which contributed options can be activated now. Unavailable actions or an unavailable participant do not necessarily destroy an episode.
3. **Consequences:** world-specific handlers apply resource transfers, relationship changes, escalation, concession, stability/strength updates, and journal effects.

An incident needs **stable instance identity, causal provenance, and a lifecycle**. A repeated visit to the world hub must not duplicate an incident; a later, genuinely new challenge involving the same nations is allowed. Identity must include a causal subject/occurrence or equivalent stable instance key, not merely type + participants.

**Policies are data, not incident subclasses.** In Crawford, all eight policy types (economic aid, weapons to the government or insurgents, intervention for either side, destabilization, treaties, diplomatic pressure) share one crisis procedure. Keep three things distinct for each policy:

1. **Policy definition:** eligible sponsor, target, magnitude, cost, and its *direct world effects* (arms reach the insurgents, aid changes the economy, a treaty creates an obligation, troops change military strength). These are what make the world move; without them the simulation degenerates into prestige optimization with cosmetic policy labels.
2. **Reaction model:** how another principal judges the policy: *Hurt* (signed harm or help to the contested nation, scaled by magnitude and the nation's vulnerability), interests, obligations, the intervention weighting, and so the likelihood of a challenge.
3. **Incident resolution:** whether the policy survives a challenge, and what escalation or concession costs each side.

All eight policies belong in the behavioral inventory; the first vertical needs only one.

A new incident specialization is warranted when its required roles, local state, behavior, or lifecycle differ meaningfully, not because a policy name changes. These vary independently: a diplomatic crisis and a long-running trade negotiation could bind the same three nations yet need different procedures (and a natural disaster with a beneficiary and two rival aid sponsors differs in roles as well). That independence is itself an argument for the eventual constellation generalization.

**The escalation ladder: likely kernel, not yet a prerequisite.** Inside an incident, the crisis is a two-sided ladder from CrisisLevel 9 down to 1 (nuclear war): on each step the side holding the ball backs down (losing prestige and adventurousness) or escalates. Crawford's decision rule (Outrage computed for *both* sides and summed into an Outrage Excess, plus a bluff term that shrinks as the crisis worsens) is a strategy supplied by the world rules. The incident owns bindings and cause; the ladder owns the escalation sequence and terminal conditions; the rules own the judgment.

Implement the ladder initially with the existing `Game`/`HasGame` integration where practical, with crisis-specific state and handler logic. Extract a reusable escalation/brinkmanship kernel after the alternating-decision semantics are settled and a second consumer appears. The open question: `GameHandler.receive_move()` resolves a player move together with a preselected opponent move in one round. A human-versus-computer crisis may fit that as "my stand-firm or back-down, then your reply", but a computer-initiated or fully readerless crisis may not.

Use the ordinary affordance system: incident type, bound roles, participating nations/powers, and world context may contribute or constrain actions. The incident is the scoped interaction receiver, *not* a private game state machine or another action bus. Preserve provider/source, acting authority, and mutation-target provenance where needed. Whether intro/choice/outro requires multiple Episode nodes is an implementation choice; **begin with one self-reentrant incident and ordinary JOURNAL projections** unless distinct graph identities prove useful.

## World scene: re-entrant coordinator

A world-scoped scene or menu is the repeatedly visited continuation point. It does not own the incident rules. Its responsibilities are:

1. Gather current world state and existing active incidents.
2. Reconcile their lifecycle and live availability without advancing simulation time.
3. Discover realizable new opportunities; provision missing incidents deterministically and without duplication.
4. Surface a required urgent incident, or offer available non-urgent incidents and ordinary policies.
5. Return from an interaction, project resulting state, and offer an explicit **advance world** action.

**Re-entry is observation/planning, not a world tick.** Inspecting the map, reviewing incidents, or returning from a choice must not trigger repeated annual updates or resources. In particular, world updates do not run in the scene's enter or exit handlers; those may journal, but only the advance action mutates world time.

Crawford's own turn order gives the scene two modes:

1. **Policy phase:** the player sets policies toward nations, each an ordinary action.
2. **Advance ("next turn"):** the only world-time mutation; its UPDATE runs the rest of the turn.
3. **Objections:** the opponent evaluates the player's policies and may question them, opening crises.
4. **World processes:** insurgency, coups, and Finlandization update each minor.
5. **News phase:** headlines report the opponent's actions and process outcomes; the player may question any of them, opening crises.
6. Return to the policy phase.

Incident escalation can take multiple local rounds within a single world interval, consistent with StoryTangl's game-round versus story-turn precedent.

**When policies take effect.** Policies chosen in the policy phase are *provisional commitments*: recorded and challengeable, with no world effects yet. The objection step settles each one (tolerated, survived a crisis, or countermanded by backing down), and only settled policies apply their direct effects in the world-process step, which is also the first point at which world-update rules observe them. Crawford's own sample turn has this shape: policies set, Next Turn, then the challenges. A single rule for when effects occur means backing down never has to reverse a journaled transfer, and revisiting a crisis cannot apply a policy twice. Open for Pass 0: whether a news-phase challenge that the opponent loses reverses an already-applied effect or only stops the policy carrying into the next turn.

Urgency is a scheduling predicate/priority, not an inherent incident subtype. A newly offered foreign-aid action may be discretionary; responding to an escalated challenge may be mandatory. An urgent incident without a legally resolvable response needs a defined automatic outcome or a clear validation failure, never an inescapable hub.

Initial opposing-superpower decisions may be resolved by a simple deterministic policy selecting from the *same offered Actions*. Human navigation of one side, AI navigation of the other, and fully readerless operation should share the rule and mutation path; no need to implement multiple live lanes here.

## First playable proof: deliberately small

**World fixture:** two principals (USA, USSR), 2–4 minors with varied alignments/proximity, one government and opposition slot per minor, a few resource counts, and a handful of relations. A map is optional. One text/Service client is enough.

**First incident:** the USA chooses to alter assistance or intervention toward a minor. The USSR can tolerate the policy or challenge it; a challenge opens an incident with at least *escalate* and *back down/concede* choices. Resolution updates one or more resources and diplomatic relationships and returns to the world scene.

**Causal continuation:** a world tick updates domestic political conditions (even with a deliberately coarse equation), and the changed state affects the next available policy or incident. A second slice can allow a coup/insurgent victory to rebind the governing_power slot without replacing the Nation.

Illustrative expected semantic trace:

~~~text
t0: USA, USSR, Nicaragua + political powers/materialized state
t1: world hub offers eligible intervention toward Nicaragua
t2: USA nominates aid/intervention -> provisional, challengeable commitment
t3: explicit advance; USSR policy selects challenge -> Incident #42 binds roles/cause
t4: USA/USSR alternate within Incident #42 -> escalate or back down
t5: crisis resolves -> policy survives or is countermanded; prestige/affinity change
t6: world processes -> surviving policies apply effects; government/opposition/stability update
t7: hub offers a changed frontier because earlier choices mattered
~~~

The trace, not authored dialogue or a polished map, is the initial acceptance witness.

## First implementation passes

**Pass 0 — audit and translation.** Inspect currently landed Episode, Role, dependency/provisioning, fanout, scoped namespace, asset-wallet, assembly, VM, journaling, and re-entrant game/sandbox contracts. Build a small Crawford-process-to-handler inventory, noting deliberate simplifications and any true missing capability; include the policy commitment/effect timing rule and how the alternating crisis maps onto the current game round contract. Don't mistake aspirational design notes for shipped APIs.

**Pass 1 — static fixture and one interaction.** Seed principals/minors/powers and relationships; construct one incident explicitly; render choices through ordinary VM/Service; execute one challenge/concession and obtain a meaningful journal receipt. No automatic generation required yet.

**Pass 2 — re-entrant hub and generative discovery.** Return from an incident to the same world scene; distinguish re-entry from world advancement; discover/provision one new incident from state; make duplicate-instance suppression and urgency ordering deterministic.

**Pass 3 — autonomous opponent and consequences.** Select the second principal's response through an initial simple policy; perform explicit world ticks; verify one chain in which earlier resource/diplomatic mutations alter later opportunities. Support a fully readerless trace with the same handlers.

**Pass 4 — recognizable BoP behavior.** Add an additional world-update process (insurgency or coup) and test that government/opposition slots can change while the Nation persists. Refine equations, data coverage, and presentation only after the narrow mechanics work.

**Later and separately:** alien/historical data swap; national / incumbent / opposition resource pools; richer event types such as natural disasters; further behavioral substitution; extraction of common ConceptConstellation responsibilities; genuinely different-domain validation; multiplayer navigator lanes (use [#346](https://github.com/derekmerck/storytangl/issues/346) / the Lost Worlds proof rather than inventing this infrastructure here); sophisticated agent models; full map/polish. Project Deikto remains a possible future consumer, not a prerequisite.

Two crisis refinements to revisit once the plain escalate/back-down ladder works:

- **Incident escrow.** Each incident holds its own stake pot: it opens in proportion to the challenged policy's magnitude and the contested nation's prestige value, and each escalation step pays more in. The winner takes the pot; a side that backs down claws back a share that shrinks as CrisisLevel rises. This makes Crawford's "loss increases with the severity of the crisis" explicit, inspectable state. Keep it a holding the principals pay into, with "winner takes" an ordinary transfer, so prestige stays a projection over relations rather than becoming a balance.
- **Attention budget.** Each principal has a bounded pool of attention or soft power per world interval, refreshed on the world tick. Escrowed attention stays locked while its incident is open, so a crisis held open in one region weakens a principal's reach elsewhere. This couples concurrent crises through opportunity cost, which Crawford's independent, sequential crises lack. Consequences: the opponent's decision rule gains an opportunity-cost term alongside Outrage Excess (record this as a deliberate departure from Crawford); crisis ordering within a turn becomes an allocation problem; and incidents may stay open across turns with their escrow intact. A strategy of continually raising stakes until the opponent can't keep up, short of war, should then emerge from the rules rather than being scripted.

## Packaging: three swappable axes

Start as a demo world (`worlds/balance_of_power/` with a `domain.py`, like `colony_loop`), but keep three axes separate from the first PR, because each planned follow-up swaps exactly one of them:

| Axis | Lives in | Swap test |
| --- | --- | --- |
| **Kernel:** escalation ladder | Crisis-specific game logic at first; `mechanics/games` once extracted | Reusable with no Balance of Power knowledge |
| **Rules:** Outrage/Hurt, world processes, opponent strategy, prestige projection | World-local rules module that reads state only through the bound concepts, never the fixture directly | *Same rules, different world* |
| **World:** nations, powers, relations, prestige values | YAML fixture | *Different rules/events, same world* |

The third follow-up, *different rules and events in a different world*, is the genuinely-different-domain test. Promote code out of the world (into `mechanics/` or a sibling example package) when there is demonstrated reuse or the world-local placement becomes awkward. A data-only world swap that needs no code move is itself evidence that the separation already works. Do not start in a separate repository: the point is to surface engine friction, not to hide it behind a consumer boundary.

## Evidence and acceptance

The core witness for the first vertical is deliberately narrow:

1. **A policy is offered and selected:** the USA proposes military aid to an opposition faction in a minor.
2. **A response is generated from world state:** the USSR evaluates Hurt, relationships, and interests, then challenges or tolerates.
3. **A crisis can resolve:** the parties alternate escalate/back-down decisions until one backs down or a terminal state is reached.
4. **Consequences are committed:** the policy survives or is countermanded; resources and relationships change accordingly.
5. **Re-entry shows a different opportunity space:** the world scene reflects the consequences with no duplicated incidents, hidden ticks, or repeated mutations.

Coups, a full resource economy, a map, all eight policies, and a second world are not needed to recognize success.

Record focused automated tests and an inspectable supported-client/service transcript demonstrating:

- First fixture loads with durable distinct nations and political powers; expected resources and relations are visible.
- Participant requirements reject invalid candidates and bind the intended actors.
- A single incident is encountered, acted on, resolved, and journaled using the existing VM.
- Re-entry is idempotent: no extra incident, no implicit simulation tick, no repeated transfer.
- New incidents are provisioned *because state permits them*, with stable identities; recurring but distinct causes remain distinguishable.
- An urgent incident can interrupt discretionary selection without soft-locking the interaction.
- A deterministic opposing policy chooses from the same legal action set as a human navigator.
- At least one consequence changes subsequent affordance availability or incident generation; no hard-coded plot-branch sequence.
- A regime change rebinds political-power slots without losing nation identity (second slice).
- Seeded replay reproduces the same semantic consequences/incident identities; record world-specific residual and any framework friction.

**Failure is informative.** If this requires bespoke parallel scheduling, action dispatch, hidden state duplication, or per-incident graph reconstruction, document the friction before promoting an engine abstraction.

## Related structure: wallets, assemblies, and incidents

An observation to keep in view, not a reason to change the plan. A wallet, an assembly, and an incident are all ways of binding existing concepts into a configuration whose relationships carry meaning and sponsor behavior:

| Structure | Binding semantics | What the configuration affords |
| --- | --- | --- |
| Wallet | Holder possesses fungible quantities and discrete member nodes, with no slots, budget, or member-to-member relationships | Spend, transfer, acquire; move members in or out |
| Assembly | Components occupy constrained functional slots | Install, replace, activate capabilities |
| Incident | Participants occupy contextual roles in a situation | Challenge, escalate, concede, resolve |

Read top to bottom, each row adds structure to the one above: a wallet is roughly an assembly with no component slots, budget, or member relationships, and an incident adds temporal identity and resolution to slot-like role binding. The assembly already sits closest to a constellation: a structure of requirement slots whose occupants contribute affordances. The [component design note](https://github.com/derekmerck/storytangl/blob/main/engine/src/tangl/mechanics/assembly/COMPONENT_DESIGN.md) has most of the vocabulary. Its *context-bound facets* are this point stated for components: the same concept contributes different behavior depending on the binding through which it is encountered (a sword in a bag offers *drop*; in a weapon slot, *attack*; in a `disputed_property` role, *claim* or *return*). Its association substrate covers when and whether a binding is admitted, and it explicitly defers an N-party generalization, which is roughly the shape an incident needs.

This world already layers the structures: a Nation is an assembly (governing and opposition slots), an incident is a constellation over nations and a policy, and a policy's direct effects act on wallets: moving quantities, moving member nodes in or out, or adjusting state on member nodes. The causal cascade (incident settles policy → policy changes wallets → wallets change capabilities → capabilities change the next realizable incidents) runs through ordinary concepts and bindings, and one concept can sit in several of these structures at once without being duplicated.

Two cautions keep the analogy honest. The structures are not one class: a wallet's fungible quantities are not individually identified participants (its discrete members are, but they carry no slot or relationship to each other), and an assembly is mostly static while an incident has temporal identity, progression, and resolution. What may generalize is the shared machinery (role-constrained membership, scoped contribution, binding changes, affordance projection), not a superclass. So when GeopoliticalIncident needs slot or binding behavior, look at assembly first as the example to copy, and record where it fits and where it doesn't. *ConceptConstellation* may turn out to name a capability that emerges from composing existing primitives rather than a new mechanic family.

## Scope boundaries and open choices

- **No first-round multiplayer** or simultaneous-action arbitration. Lost Worlds is the independent first-class multi-lane test; this world can adopt those navigator facilities later.
- **No up-front ConceptConstellation framework.** Start from GeopoliticalIncident and extract shared facets by polymorphism and composition when justified.
- **No full-fledged political hierarchy.** Nations and a government/opposition split are sufficient; recursive leaders, parties, dynasties, and contested sovereignty can be introduced without changing the premise.
- **No requirement for physical-model or historical precision.** Crawford's process logic and recognizable outcomes matter; calibrated numbers can be revisited.
- **No requirement for rich client/media.** Same semantic output should project through text first; a map is a view of already-semantic geography.
- **Avoid confusing national stock with government ownership, or provisioning with availability, or planning with world-time mutation.**

Unresolved design decisions worth resolving in code, not with a speculative framework: whether political powers should be actor concepts or tokens; which resource quantities belong in wallets versus state; the minimal durable cause/identity key for incidents; where urgency is computed; and which existing hooks implement multi-source affordance contributions most cleanly.

## Pointers and ownership

- [World Designs catalog](index.rst) and [mechanics family design](../design/story/MECHANICS_FAMILIES.md): demo posture and proof standards.
- [Open-link / affordance model](../design/planning/AFFORDANCE_MODEL.md), [hub fanout](../design/story/HUB_FANOUT.md), [interaction vocabulary](../design/story/INTERACTION_VOCABULARY.md): composition rails; some convergence remains proposed.
- [#255](https://github.com/derekmerck/storytangl/issues/255) / [#332](https://github.com/derekmerck/storytangl/issues/332): scoped sponsorship and mechanics reuse, not permissions to build a parallel subsystem.
- [#643](https://github.com/derekmerck/storytangl/issues/643): related, separately parked social-drama research. This geopolitical proof does not automatically unpark it.
- Chris Crawford, *Balance of Power* (1985); *Balance of Power: International Politics as the Ultimate Global Game* (1986), especially chapters on insurgency, coups, Finlandization, and crises. Primary model reference; this pastiche explicitly permits interpretation and simplification.

This brief captures design intent and a first bounded proof. The linked implementation issue is the authority for live task progress, and the eventual world's README should state what actually ships.
