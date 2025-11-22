Probit-d20
==========

**Probit-d20** is a generic "rules-light" rpg stat system with intuitive ability and challenge ranks tied to the statistical normal distribution.

Any task can be converted into a probit (probability unit) for success and resolved with a uniform random sampler, like dice rolls, coin tosses, or card draws.  d20 is particularly easy to map onto the normal distribution $N(10,3)$, which inspired the name.

Alternatively, 4d6-4 generates a decent approximation of $N(10,3)$ in a pinch when using probit is undesirable.


Measured Qualities
==================

Any "quality" can be quantized into 5 levels.  The basic idea is that the normalized quality delta between "difficulty" and "competence" represents the likelihood in standard deviation units required to succeed at a task.


Quality Ranks
-------------

| rank      |    |
|-----------|----|
| very poor |  1 |
| poor      |  2 |
| ok        |  3 |
| good      |  4 |
| very good |  5 |


Intrinsic Qualities
-------------------

Measures of raw ability like body, mind, spirit.

Intrinsics may have a nominal permanent value, and a current value, which may be lower (body is sick, mind is injured) or higher (spirit is blessed). 

Permanent values may increase or decrease _very slowly_, through exercising or ignoring related domain traits, injury and recovery, or through expensive evolutions or upgrades.

Current values represent the health of that aspect and may change relatively dynamically, particularly in case of injury.  If the current value of any intrinsic hits 0, that character is considered disabled/broken until the value can be repaired to at least 1 (or the char dies).


Domain Qualities
----------------

Measures of craft like skills, equipment, furnishings, or followers.

Domain values may progress or decay _slowly_ through exercising or ignoring the trait, or through evolutions or upgrades.  

Exercise quality is based on the relative difficulty of the task (hard is worth more than easy), the current trait level (low improves faster than high), and the outcome achieved (failures count more than successes).


Currencies
----------

Characters have wallets of fungible tokens that can be invested or replenished through various game mechanisms.  

An obvious example could be "cash", which could be used to buy benefits from traders or collected from defeated monsters, for example.  

Currencies may be tied to intrinsics or domain qualities, like stamina may have a max value equal to 2x current body and recover each night according to the furnishing domain (better recovery in a bed than on the street).


Tasks and Resolution
====================

Overview
--------

- Any measured quality can be remapped to five-point range from -2.5 to 2.5, centered at 0, which represents "average".

- Taskees have _intrinsic_ qualities (body, mind, etc.) and _domain_ qualities (skills, equipment).  Each domain is governed by a specific intrinsic.  A taskee's _domain competency_ is the average of the domain quality and its governing intrinsic quality.  Fighting by body, learning by mind, etc.

- Tasks have a _difficulty_ rank, _domain_, and _tags_.  They may also have a _cost_ and an _reward_.

- Situational effects are applied dynamically based on the difficulty, domain, or tags.  A situational effect may provide a bonus or malus to the relative challenge, cost, outcome, or even change the task domain.  For resolution, all dynamic bonuses and maluses are summed and then clamped (-2.5, 2.5).

- The _relative challenge_ of a task is the normalized total of:
    $$ ( competency - difficulty + dynamic ) / 3 $$
  This will again range -2.5 to 2.5, ( -2.5 competency - 2.5 difficulty - 2.5 malus = -7.5/3 to 7.5/3 = 2.5 competency - -2.5 difficulty + 2.5 bonus)

- The task can be _resolved_ by considering the relative challenge as the standard deviation quantile on N(0,1) to beat. For a very easy challenge (-2 std dev), we will succeed about 90% of the time.  For an easy challenge (-1 std dev), we succeed about 35% of the time.  For an average challenge (0), we will succeed 50% of the time.

Depending on the test value, the _outcome_ of the task is returned as a quality rank (bad failure, failure, inconclusive, success, major success)

- If the character can pay the modified task cost (perhaps stamina), they can test the relative difficulty of the task to resolve it (yield an outcome)



Difficulty Rank
---------------

| rank      | difficulty |    |
|-----------|------------|----|
| very poor | very easy  | -2 |
| poor      | easy       | -1 |
| ok        | normal     |  0 |
| good      | hard       |  1 |
| very good | very hard  |  2 |


The base or relative difficulty level of a task.

Likelihoods are balanced so that it is intuitive to tune encounters around an average ability and training character doing a common task has about a 50% success rate, an average character doing a hard task or a novice doing an average task has about a 35% chance of success (1 std dev below the mean), whereas a skilled character doing an easy task has an 90% chance of success (2 std dev above the mean). 


Extrinsics
----------

Dynamic modifiers based on domain or task tags can provide bonuses or maluses, like 'has sword #fight+1', 'hands tied, #agility-1', ...

Situational modifiers can be assigned intuitively given the insight that +/-2.5 provides nearly a full level of mastery or impairment.  Multiple situational modifiers may be applied, but their sum total must be clamped to the standard range (-2.5 malus, 2.5 bonus).


Relative Challenge
------------------

Competency is the average of the domain quality and its governing intrinsic.


Resolution
----------

### Likelihood of success

Normal distribution, value > relative difficulty - 3 std dev

i.e., normal success = > 50%, easy success = random > normal -1x std, very hard success = random > normal 2x std

Above the required value for the next std dev up = big success
Below the required value for the next std dev down = big failure

The normalized average of positive traits and negative traits is the _relative difficulty_.  Note range is [-10, 10], ie ((1+1+0) - (5+5+2)) or vice versa. 

relative difficulty = (difficulty - competency + 10 ) / 20

### Dice rolls

competency dice = 1 dice for each point of competency (1-5)
difficulty dice: 1 dice for each point of difficulty (1-5)

roll all dice, sum competency dice and difficulty dice separately.

success on competency sum > difficulty sum, if 1 on any competency dice, big success
failure on competency < difficulty, if any 1 on difficulty dice, big failure

### d20

- very easy: roll better than 2 (90%)
- easy: roll better than 7 (65%)
- normal: roll better than 10 (50%)
- hard: roll better than 13 (35%)
- very hard: roll better than 18 (10%)

### Opposed challenges

There are two kinds of challenges:

- environmental (e.g., burgling), which uses (2*task challenge + extrinsic malus) / 10, clamp(1,5) as difficulty
- opposed (e.g., fighting), use opponent competence as difficulty

For opposed tasks, resolve both agents simultaneously.  Both parties can be successful, or unsuccessful, or a combination.

Outcome Rank
------------

| rank          |    |
|---------------|----|
| bad failure   |  1 |
| failure       |  2 |
| near failure  |  3 |
| success       |  4 |
| major success |  5 |


Inspirations
============

- [Fudge](https://www.fudgerpg.com/about/about-fudge/fudge-overview.html)
- [Tiny-d6](https://www.gallantknightgames.com/tinyd6/)
- [d6xd6](https://d6xd6.com/)
