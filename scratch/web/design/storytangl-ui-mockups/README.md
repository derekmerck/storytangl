# StoryTangl UI Mockups

Copied from `/Users/derek/Desktop/tangl working/` on 2026-04-23 as scratch
reference material for future web-client work.

## Contents

- `StoryTangl UI/` contains the source HTML, CSS, JSX, and fixture files.
- The two print PDFs are static exports of the v1 and v2 wireframes.
- `StoryTangl UI/v2-fixture.js` is the most useful implementation reference:
  it defines one `RuntimeEnvelope` plus one `ProjectedState` consumed by all v2
  shells.

## Reading Notes

The v1 mockup is a broader shell tour: dossier, scroll, stage/log, visual novel,
card deck, terminal, widget catalog, and author/debug mode.

The v2 mockup is more directly useful for the current app because it is shaped
around the live engine contracts:

- canonical `RuntimeEnvelope.fragments`;
- sidecar `ProjectedState.sections`;
- group membership by stable fragment UID;
- stream `kv` versus durable projected `kv_list`;
- locked choices with user-visible reasons and structured blockers;
- freeform choices with an `accepts` contract;
- pending media via stable media fragments;
- invisible control/update fragments that require stable target UIDs;
- port-parity fallbacks for web, CLI, Ren'Py/Godot, and terminal clients.

## Web Test Harness Implications

When revising `apps/web` tests, prefer a canonical fixture module modeled after
`v2-fixture.js` over the current small lorem-ipsum block fixtures. The fixture
should exercise a whole turn:

- content, attributed dialog, media, group, kv, choice, control/update, and
  user_event fragments;
- projected scalar, kv_list, item_list, table, and badges sections;
- available, locked, and freeform choices;
- resolved URL media and unresolved RIT/pending media;
- group flattening by `member_ids` and fallback rendering for unknown groups.

The current Vue client still normalizes canonical fragments down into legacy
`JournalStoryUpdate` blocks. A harness refresh should decide whether the unit
tests keep proving that compatibility layer, or whether new component tests
should target a first-class fragment/widget vocabulary directly.

Also keep the v2 accessibility expectations in scope:

- choice groups should have stable keyboard order and labels;
- locked choices should remain visible and disabled with a reason;
- freeform choices should commit payloads explicitly;
- fragment logs or active story regions should use polite live-region behavior;
- pending/error/fallback states should preserve stable DOM targets so later
  control fragments can update them.
