Look Mechanic
=============

There are 3 inter-related parts to an Actor's "Look"

1. Body traits (hair, eyes, skin tone, etc. depending on exposed features)
2. Outfit (wearables)
3. Ornaments (tattoos, piercings depending on exposed features)

There are also optional dynamic state-based factors:

4. Attitude
5. Action or pose

The Look handler implements two main public interfaces:

1. `describe(actor, *state)`: produce a _narrative description_ of the actor, optionally given state, pose, and/or attitude
2. `media_spec(actor, *state)`: produce a media spec for the character, either as a paperdoll or a portrait, optionally given current action, pose, and/or attitude

Look also provides access to the OutfitManager attribute, which allows changing wearables or wearable states (open, close, remove) and the OrnamentManager attribute, which allows updating those features or forcing an outfit to cover/show a particular feature.

Outfits and Ornaments depend heavily on the BodyRegion enum ontology to determine feature coverage.  BodyRegion is composed of overlapping flags, so it can represent a range of scales, from the simplest HEAD, UPPER_BODY, LOWER_BODY partition to individually addressing the ARMS (part of UPPER_BODY), RIGHT_ARM (part of ARMS), or even RIGHT_HAND (part of RIGHT_ARM).
