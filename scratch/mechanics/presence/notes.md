Look Mechanic
=============

The complexity here is a bit out of proportion, but humans have a _very_ powerful eye for appearance and consistency details in other humans, hence the 'uncanny valley' phenomena.  We want to track as much as possible regarding important characters' general presentation, as well as their specific presentation in a given situation. This provides continuity for dynamic descriptions and media.

There are 3 inter-related parts to an Actor's "Look"

1. Body traits (hair, eyes, skin tone, etc. depending on exposed features)
2. Outfit (wearables)
3. Ornaments (tattoos, piercings depending on exposed features)
4. Vocal profile (not really 'look' but same mechanism)

There are also optional dynamic state-based factors:

4. Attitude
5. Action or pose

The Look handler implements two main public interfaces:

1. `describe(actor, *state)`: produce a _narrative description_ of the actor, optionally given state, pose, and/or attitude
2. `adapt_media_spec(spec_type, actor, *state)`: produce a media spec for the character, for example as a paperdoll or a portrait or a TTS profile, optionally given current action, pose, and/or attitude

^ These are basically a mini-dispatch that other systems can hook into to provide handlers.

**Look** also provides access to the **OutfitManager** attribute, which allows changing wearables or wearable states (open, close, remove) and the OrnamentManager attribute, which allows updating those features or forcing an outfit to cover/show a particular feature.

Outfits and Ornaments depend heavily on the BodyRegion enum ontology to determine feature coverage.  BodyRegion is composed of overlapping flags, so it can represent a range of scales, from the simplest HEAD, UPPER_BODY, LOWER_BODY partition to individually addressing the ARMS (part of UPPER_BODY), RIGHT_ARM (part of ARMS), or even RIGHT_HAND (part of RIGHT_ARM).
