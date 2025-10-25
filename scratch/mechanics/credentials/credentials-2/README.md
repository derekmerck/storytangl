Credentials Mechanic
====================

The credentials mechanic is heavily inspired by the Lucas Pope's [Papers Please][].  Paper's Please is an innovative, narrative driven variant of a "Spot the Difference" game.  To a lesser extent it is also influenced by clones of Paper's Please like the NSFW game [Imperial Gatekeeper][].

[Papers Please]: https://papersplea.se/
[Imperial Gatekeeper]: https://f95zone.to/threads/the-imperial-gatekeeper-v1-75-tengsten.33616/

In each encounter, the player is presented with a list of rules for indications and outcomes, a candidate, and their credential packet.  The player must determine if the credentials are accurate, complete, and valid given the rules, and then disposition the candidate accordingly.  

The core interaction is implemented as a "PickingGame", where the player can pick discrepant features from the game setup and from the candidates _presenting indication_ to reveal the candidate's _real indication_, and then select a disposition.  Additional specialized story infrastructure in Challenge blocks and scenes handle automatic encounter generation, extras, and narrative flow management.

Credential Check
----------------

There are several basic elements to the encounter:

- A set of _rules_ with dispositions for all possible candidate _indications_: "allowed", "allowed with ticket", "allowed with id", "allowed with permit and id", or "disallowed".

- The candidate's true _indications_: the rule set that applies to them, and the reason why they need credentials.  Indications are divided into "origin", "purpose", and "contraband" categories.

- The candidate's _presentation_, which is made up of their declared indications and their supporting credentials.  Their identity and other indications may be falsified or hidden in the presentation.  Invalid credentials (incomplete, incorrect, or falsified) may be presented.

- Finally, the _expected disposition_ for the candidate.  The ideal disposition for that candidate, based on the applicable rules and indications, and any discrepancies in their presentation. Dispositions are "allow" (default), "deny" (incomplete or incorrect), or "arrest" (falsified).  The expected disposition is used for overall scoring.

- There are two additional factors that weigh into _disposition_: a _blacklist_ for undesirables and a _whitelist_ for immune candidates.

- A candidate that has been exposed as incomplete, invalid, or falsified may try to haggle for a better outcome, through bribes or threats, which can influence the overall narrative in different ways.  One of my favorite candidates in "Papers, Please" bribes you for a red stamp, a denial, even though they have valid credentials.  They need the red stamp to prove that they are not allowed to work.

Automatic Media Generation
--------------------------

Using templates, the CredentialForge can automatically generate valid or invalid holder-portrait-images and seal-images for id cards and permits.

This is done as a pre-process, then candidate extras are generated to match (or not) one of the pool of pre-generated candidate id photos.