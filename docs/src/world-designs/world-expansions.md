# Existing-World Expansions

These directions extend experiences whose smaller executable worlds exist. The
baseline links describe what ships; the proposals claim no additional content,
media, or coverage. The [showcase portfolio](https://github.com/derekmerck/storytangl/issues/395)
owns the shared implementation direction unless another issue is linked.

## Coronate the Regent: preparation becomes a personal record

**Stage:** expansion brief seed.
**Baseline:** [Coronate the Regent](https://github.com/derekmerck/storytangl/tree/main/worlds/coronate_the_regent).

**Premise and invariant.** Four weeks of preparation turn training, purchases, and
provocations into a later reckoning. Make the court and its judgment feel inhabited
without diluting the deadline or hiding the costs of neglected duties.

**Existing rails.** Finite training, durable stats, wallet costs, mood effects, the
prince, dragon, sword hedge, and endings supply a dramatic skeleton. A generic
pacing or story-sifting system is not needed to write connective scenes.

**Proposed composition.** A recurring chamberlain, brief inter-week scenes,
escalating dragon rumors, a prince with an objective, and endings recalling specific
choices. [Salon Season](salon-season.md) is a separate story; grafting its revolution
onto this fixture remains deferred.

**Concrete presentation opportunity.** The existing burning-valley plate
deliberately contains no dragon: the creature was intended to occupy the air as a
separate staged sprite. Supplying that sprite would complete an explicit visual
design, rather than require repainting the background or changing the preparation
mechanics. See the world's
[art note](https://github.com/derekmerck/storytangl/blob/main/worlds/coronate_the_regent/README.md#two-things-the-art-deliberately-does-not-do).

**First playable proof / unlock.** One connective scene and one attributable ending
callback, retaining the existing preparation/outcome witnesses. This is the lowest-
risk test of authored rhythm and voice over current mechanics. Choose a sibling
if added content would obscure the compact proof.

**Separate platform work.** [#448](https://github.com/derekmerck/storytangl/issues/448)
owns account achievements and a Coronate NG+ entry. Story-local achievements do not
establish account persistence. That work may support returning-player content but
is not a prerequisite for this narrative experiment.

## Marmoset Island: social and audiovisual expansion

**Stage:** expansion seed; detailed new plot not yet specified.
**Baseline:** [Marmoset Island / Marmoset Orbital Station](https://github.com/derekmerck/storytangl/tree/main/worlds/repartee_loop).

**Premise and invariant.** Learn repartee by losing, retain a repertoire, and use it
to gain opportunities. A social expansion could make the people who teach, oppose,
or reward that repertoire matter outside the immediate contest.

**Existing rails.** The launchable world combines acquisition, contests, and
aftermath. Island/station packs share prose, graph, and staging semantics; music
and optional animation are existing presentation evidence, not new requirements
invented by this brief. Optional art still needs a playable text/still floor.

**Concrete media baseline and opportunities.** The spaceport pack already has
`idle`, `call`, and `response` animation sheets; the quayside pack stages the same
clips but currently draws stills. Adding quayside sheets is a specific presentation
completion opportunity over the same graph and client contract.

Persistent BGM playback in pygame, including the Marmoset opening cue, landed in
[#583](https://github.com/derekmerck/storytangl/pull/583).
[#571](https://github.com/derekmerck/storytangl/issues/571) retains the separate
unimplemented Web BGM consumer: browser unlock, fetch/decode/play, and reconnect
behavior.
The remaining delivery gap is Web playback, alongside the pack-specific artwork
opportunities above.

**First playable proof / unlock.** Choose one opponent and add a before/after
callback keyed to a learned response or outcome. Test whether social continuity
strengthens the learning loop. A separate presentation pass can enrich the same
beat through existing media delivery without storing another version of its facts.

**Unresolved questions.** What changes beyond winning access? Which audiovisual
additions improve that experience instead of simply adding assets? The existing
README also proposes a future spaceport *cover* of the island theme; that is a
media-generation experiment, not a new backend music contract.

## Grand Grotto: a recurring companion

**Stage:** expansion seed.
**Baseline:** [Adventure sandbox slice](https://github.com/derekmerck/storytangl/tree/main/worlds/adventure_sandbox_slice).

**Premise and invariant.** Aid to a wounded pirate costs time or light, but changes
knowledge, hostility, companionship, custody, or betrayal on later journeys.
Returning through familiar space should expose the consequences of whom the player
helped and what they spent.

**Existing rails.** Locations, inventory, light, locks, time, and ordinary projected
opportunities already have a spatial conformance world. A mobile, recurrent
companion sharing those resources remains a proposed composition, not proof of a
generic companion mechanic.

**First playable proof / unlock.** One aid decision, a resource consequence, and
one changed return route or encounter with the same person. Preserve the compact
sandbox fixture. Give a story-bearing sibling an original setting and move technical
self-description into its README. This can expose scheduling/scoped-opportunity
friction without importing Patient Zero's entire configuration problem.

**Unresolved question.** How does remembered aid and the companion's own schedule
or willingness change exploration without making every room an event hunt?

## Hungry Colony: attrition gets names

**Stage:** expansion seed.
**Baseline:** [Hungry Colony](https://github.com/derekmerck/storytangl/tree/main/worlds/colony_loop).

**Premise and invariant.** Production becomes force, force is risked in a raid,
and attrition/reward changes the colony producing the next force. Dark comedy and
named workers would make the cost of those counters perceptible.

**Existing rails.** The production/raid/aftermath loop already feeds consequences
back into the shell. Named roles, queen demands, rivals, and threshold scenes are
proposed uses of that state, not a second economy or generic memory framework.

**First playable proof / unlock.** Name one worker, establish one colony need,
and write two aftermaths distinguishing a prior allocation or loss. Preserve the
deterministic loop. Ask whether the same resource transition acquires social and
comic meaning without another state authority.

**Unresolved question.** Which losses persist as individuals or roles, and which
remain aggregate attrition without misleading the reader about who died?
