# Casting Desk

**Intent:** show how a world completes a small, authored cast once, then reads the
same individuals through ordinary prose, choices and JSON service persistence.

Three files wait on the desk:

- **River Guild:** Ari keeps an authored given name and adult age band; UPDATE
  fills a family name and gender from explicitly requested dimensions.
- **Hill Guild:** another human keeps an authored neutral gender and intentional
  absence of a family name. Only the given name and age band are generated.
- **Grove Kin:** a sprite gets a given name and compound family name, such as
  Hydrangea Cinnamontwinkle. No country, gender or age is requested or invented.

The two guilds are distinct authored `Origin` values that deliberately share the
world's `salon` bank. Origin does not imply nationality. All three applicants select
the `female` form explicitly, independently of profile gender. These are illustrative
pools and simple age/gender policies, not representative population data.

## Play

From the repository's normal CLI session:

```text
create_user casting-reader
create_story casting_desk
do 1
do 1
```

Open a file, inspect its profile, and return to the desk. The three menu entries
refer to three fixed applicants. Opening another file uses another already
allocated slot; reopening a file preserves its name, facts and completion receipt.
“Read profile again” only inspects. “Close the desk” ends the walkthrough.
`run_script worlds/casting_desk/cli_witness.txt` runs the maintained example after
creating a user. Its assertions live in the CLI witness harness.

## What the bundle demonstrates

`script.yaml` declares all actors, roles, requested dimensions, partial values,
and forms. Ordinary eager template materialization creates the three
slots before generation. The world domain reads its own banks from
`resources/names/` and publishes that bounded catalog through the existing module
authority seam. It registers no national pack: a world that brings its own banks
needs none. Importing the generic demographics package does not adopt this world
or load its data.

## Name banks

Each file in `resources/names/` is one authored `NameBank`: a label, a world-local
`selection_key`, a revision and its forms. Pools shared between forms use a YAML
anchor rather than a second copy.

| File | Key | Shape | Provenance |
| --- | --- | --- | --- |
| `salon.yaml` | `salon` | given + surname, `female`/`male` | Salon Season remix resources, entries verbatim |
| `sprite.yaml` | `sprite` | given + stem·suffix family, `female`/`male` | the retired faie-cities sketch |

These banks are parked here so they are not lost. When the Salon Season or a
faie-cities world lands, move its bank into that world and have Casting Desk borrow
it rather than keep a second copy. Leaving them here as references is also fine;
the rule is one copy, not where it lives.

Borrowing a bank from another sideloaded world, rather than from a pack, is not
built yet. Today a world can only compose catalogs it constructs itself, so the
direction to settle is how one world names another world's published banks without
importing its domain module.

An explicit world UPDATE handler completes only the current `applicant` role and
commits the returned `personal_name`, facts and receipt using the VM-supplied frame
RNG unchanged. Identical versioned inputs and explicitly supplied RNG seeds reproduce
values and post-draw RNG states in controlled contexts. Independent stories can
have different VM seeds because their runtime identities differ; their applicant
values need not match. Fully authored completions and revisits leave RNG untouched.

Prose's `reference(..., form='full')` and the actor's normal namespace read the
same actor-owned `PersonalName`. Inspection includes origin, requested profile
facts and bank/form/revision provenance. No display-name cache or second name is
stored. Ordinary JSON service restoration bootstraps the declared world/catalog
before restoring live bank references and continues play without sampling.

Maintained witnesses cover all three service paths, preserved authored values,
targeted completion, controlled-seed reproducibility, unchanged IDs/receipts on
revisit, current-name prose, no-draw reads, cold JSON restore and cmd2 play.

This is a finite, text-first consumer. Dynamic actor creation, a regenerate button,
credentials, Presence/outfits, portraits and voice are separate follow-ups. Required
play and tests need no full name pack, LFS, network, graphics or model worker.
