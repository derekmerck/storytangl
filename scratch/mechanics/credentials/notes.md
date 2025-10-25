The screening game is a "spot the difference" variant on the Hidden Object game-type.

Multiple sets of facts, rules, and evidence are introduced, the player must uncover hidden evidence and identify discrepancies.

Paper's Please
==============

Scenario Facts
--------------

Scenario facts are given, but may be missing, hidden, or forged.

- presentation (image)
- name
- id num
- origin
- purpose
- contraband (possibly hidden)
- docs (possibly missing, hidden, or forged)

Scenario rules are given, may be updated from day to day.

Processing
----------

Check for rules:

- not on blacklist (person, origin, purpose, contraband) -> deny or arrest per rule
- no undocumented or hidden contraband
- official credentials (sealed)
- correct for person (presentation, name, id, origin)
- correct for purpose (supplements)
- correct for contraband (permits)
- passed all -> allow

Check for whitelist:

- is on whitelist (person, origin, purpose, contraband) -> allow

There are only a few possible interactions:

- Indicate a distractor (non-discrepant item, 'that seems in order')
- Indicate a discrepancy (request a clue to clear or confirm)
- Deny (optionally with reason)
- Arrest (optionally with reason)
- Allow

Distractors:
-----------

- Indicate correct seal
- Indicate non-required official credential
- Indicate required official credential
- Indicate correct holder for ID
- Indicate allowed origin
- Indicate allowed purpose
- Indicate allowed patent contraband

Discrepencies:
-------------
- Clear possible hidden contraband (always)
    -> _search_ or -> deny
    -> accept and clear
    -> accept and discovered contraband
      -> if permitable: produce permit to clear or deny/arrest (smuggling)
      -> otherwise: deny/arrest (smugging)
- Indicate unofficial credentials
    -> missing seal -> deny
    -> wrong seal -> deny/arrest (forgery)
- Indicate _missing_ required ID
    -> _produce_ to clear or deny
    -> declines -> deny
    -> accept and clear
- Indicate _wrong_ required ID
    -> verify id to clear or confirm
    -> declines
    -> confirmed wrong ID -> arrest (identify fraud)
- Missing permit for purpose
    -> if permitable: produce to clear or deny
    -> otherwise: deny
- Missing permit for patent contraband
    -> if permitable: produce permit to clear or deny
    -> otherwise: deny
