Stat Domain Progression Mechanic
================================

The stat domain progression system is a generic 'stat' framework as described in most RPG type games.  It includes stat tracking, challenges, growth, and situational effects.  The progression system determines how costs are paid, outcomes are evaluated, and rewards or penalties are assessed for Challenge Blocks.


Stat Tracking
-------------

### Measures, MeasuredValues, and StatDomains

Measures are general magnitude classes for measuring quality, difficulty, or impact. Measures are enumerated qualifiers like small to large, poor to good, etc.

MeasuredValues are floats that also test as Measures.  They can be incremented in tiers or fractions of tiers, or by directly manipulating the underlying float value.  MeasuredValues have a float-value ('fv') range of 0.0-20.0, which maps to a quantified integer-measure ('qv') range of 1-5.

StatDomains are abstract domains, like Body, Mind, Charm, etc.  Each stat-domain may define its own Measures.

### Stats, StatMaps

Stats are a MeasuredValue associated with a particular StatDomain.  This can be done collectively through a mapping of StatDomains to MeasuredValues, or represented individually as Stat objects.

Stats can be compared against any other stat type that uses the same 1-20fv/1-5qv basis.

### StatCurrencies

Stat domains also have associated _currencies_ that are routinely spent and restored, for example, "health" for the "body" domain or "wit" for the "mind" domain.  Stat currencies are implemented as CountableAssets and managed by Wallets (counters) keyed by stat domains.


Tasks
-----

StatCurrencies are gained or lost primarily through _Tasks_. Tasks have a _cost_, a _difficulty_, and a _payout_.

When a tasker pays the task's StatCurrency _cost_, they can test the task _difficulty_ to get an _outcome_.  Then, based on the measure of the outcome, they will receive a payout.

A task with a single-domain difficulty is a relative-distance-stat-test.

_Tasks_ rely on the _TaskHandler_ to orchestrate the interaction between the tasker node (possibly a proxy for the player), any applicable situational effects, and the Task itself.

Tasks are driven by StatMaps and StatCurrencies in 4 places:

1. Conditions may include Stats thresholds for availability
2. Cost is a StatCurrency wallet, paid by tasker on attempt
3. Challenge difficulty is one or more target Stats for computing the task/tasker delta
4. Payout is a StatCurrency wallet, received by tasker according to outcome

The _StatChallenge_ class is a Block mixin that wraps a Task with a narrative context.  Activities could include combat, conversation, stealth, or any other system a game uses.


Difficulty
----------

_Difficulty_ is represented as a Stat of the appropriate domain and level. 

_Relative Difficulty_ is computed by finding the difference between the task difficulty and the tasker's relevant stat, and then converting that distance to a relative probability of success.  Typically, a high skill and low difficulty will have a high chance of success, and vice versa.

Example:

- impossible (5%) (two ranks up, i.e., impossible + practiced, hard + novice, challenging + unskilled)
- hard (25%) (one rank up, i.e., impossible + master, hard + practiced, challenging + novice, easy + unskilled)
- challenging (50%)  (same rank, impossible + expert, hard + master, challenging + practiced, easy + notice, trivial + unskilled)
- easy (75%) (one rank lower, i.e. hard + expert, challenging + master, easy + practiced, trivial + notice
- trivial (95%)  (two ranks lower, i.e., challenging + expert, easy + master, trivial + practiced)


Situational Effects
-------------------

SituationalEffects map between tags and Task parameters.  They can increase/decrease, modify, or remap a task's _cost_, _difficulty_, or _payout_.

The TaskHandler will aggregate costs, difficulties, effects and generate outcomes.

A situational effect may enhance or diminish the _measure_ of a cost, difficulty, or outcome of an event, for example, making the cost more expensive or the difficulty easier.

Or it may _alter_ the cost domain, difficulty domain, or outcome domain of an event, for example, a "cheating" effect might swap a skill difficulty for a cash cost.

Situational effects on taskers or tasks are applied whenever the effect's tags are a subset of the activity's tags.

Effects are described in terms of the _applicable tags_, and the _task attribute_, and the _adjustment_.

For example:

```yaml
applies_to_tags:    { #task1 }
available: false    # force activity availability or lock
cost: down          # cheap (down), dear (up), swap key, invert
difficulty: harder  # easy (down), hard (up), swap key, invert
outcome: bonus      # malus (down), bonus (up), swap key, invert
```

The 'invert' outcome adjustment indicates that the _opposite_ effect is achieved.  ie, increase in A becomes decrease A or increase in ~A

Effects can be added to a task as _tags_ using a shorthand format:

```
#x, task activity is in domain 'x'

@x+cost-up/down, increased/decreased cost in #x activities
@x+difficulty-up/down, increased/decreased difficulty in #x activities
@x+payout-up/down, increased/decreased reward in #x activities

@x-up, decreased cost, difficulty, increased reward in #x activities
@x-up-up, ...
@x-down, increased cost, difficulty, decreased reward in #x activities
@x-down-down, ...

@x-cheap/dear -> x+cost-down/up
@x-easy/hard -> x+difficulty-down/up
@x-bonus/malus -> x+reward-up/down

@x-inv, invert rewards in #x activities
@x-is-y, remap #x domain activities to #y
@x-prohibited, cannot do #x activities
```

example:

```
>> npc = Npc(
>>   quality = {'str': MEDIUM},
>>   tags = {'@cbt-up'}
>> )
Npc(...

>> cbt_task = Task(
>>   difficulty = {'str': HIGH},
>>   tags = {'#cbt'}
>> )
Task(...

>> cbt_task.effective_difficulty(npc)
{'str': MEDIUM}

>> cbt_task.do_task(npc)
PASS

>> generic_task = Task(
>>   difficulty = {'str': HIGH},
>> )
Task(...

>> generic_task.effective_difficulty(npc)
{'str': HIGH}

>> generic_task.do_task(npc)
FAIL
```

Badge assets are a useful way to bridge tags to situational effects.


Improvement
-----------

Exercising stats can improve them over time.  This is also a function of the  stat handler assigned to each particular stat.

improvement on _challenge_:
- challenge level is the discrepancy between tasker skill and task difficulty
- Success:  0.0 ... 0.5 (base for relative challenge, trivial -> impossible)
- Failure:  0.0 ... 1.0 (*2)

improvement on _training_:
- challenge level is inverted discrepancy between learner and master, i.e, expert teaches unskilled as a 'hard' task, master + novice = easy, same level or lower is always 'trivial', so no gain.
- Success: 0.0 ... 1.0 (*2)
- Failure: 0.0 ... 0.5
