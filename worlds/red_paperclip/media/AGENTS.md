# Why this pack ships binaries

Seven 320x200 PNGs — one map plate and six hub backgrounds — committed to
regular git rather than LFS.

**They are required.** Every one is named in `script.yaml` as block media, and
the map plate is load-bearing beyond decoration: without it the road is a
numbered list rather than a clickable district, which is the feature this world
exists to exercise in the pygame client. `test_scene_plate_packs.py` reads
their bytes: it decodes each plate with `Image.load()` and hashes the file,
because `open` reads a header and defers the pixels, so a truncated plate
reports its declared size and mode quite happily. That decode is why they are
not in LFS (root `AGENTS.md` media rule 3) — a test that reads bytes cannot
depend on LFS having materialized — and for the same reason they must survive
`git archive`, which `test_shipped_assets_survive_archive.py` pins.

**They cannot be SVG.** Rule 1 prefers vector for anything vector-shaped. These
are dithered raster scenes with tens of thousands of colours; there is no vector
form.

**They are shipped assets, not source.** Each is conformed from a 1280x800
render to the client's logical surface. The generation-size originals are not
committed — rule 2 — and are reconstructible from `provenance/jobs.json`, which
records the workflow, models, parameters, prompts and seeds. The per-asset
`*-receipts.json` beside it are the runner's own receipts for the same jobs,
kept because they carry the fully rendered workflow rather than a summary of it.

**No reference images.** Unlike `hall_monitor` and `coronate_the_regent`, these
were rendered from text alone, so `references` is empty and every job records
`reference_sha256: null` rather than omitting the field. That is a claim, not an
absence: nothing but the prompt conditioned these.

**Seven, and six of them are one each.** A hub the world visits gets a plate; a
hub it does not have does not exist. The map is the seventh because the road is
a place you stand in, not a menu. Rule 5 says pause at dozens.

## The geometry is not in here

`script.yaml` owns the six map regions, measured against `district_map.png`
after it was drawn. Re-rendering the plate moves the landmarks and the regions
have to be re-measured by eye; nothing derives one from the other, which is the
same trade `repartee_loop` makes (issue #419).
