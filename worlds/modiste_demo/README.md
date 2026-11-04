# The Modiste's Catalogue

**Intent:** demonstrate world-scoped ingestion of a small Afreet-derived SVG
catalogue for the [Salon Season design](../../docs/src/world-designs/salon-season.md)
and [#661](https://github.com/derekmerck/storytangl/issues/661). Maintained witnesses
are `engine/tests/loaders/test_modiste_demo_world.py`,
`engine/tests/loaders/test_modiste_service.py`, and
`engine/tests/media/media_creators/svg_forge/test_svg_plan.py`. The story provides a
textual recipe and resolved-plan exhibit; it does not render or assemble a character.

From a normal CLI session, run `create_user modiste-reader` followed by
`create_story modiste_demo`; use the outfit and palette choices to update the
recipe and inspect its parts, bindings and plan identity.

The world media compiler indexes `resources/` through `ResourceManager`.
`modiste_demo.domain.load_pack(world.resources)` reads the world-owned collection
and palette declarations and indexes their selected SVG groups with the shared
`svg_forge.svg_catalog` kernel. The returned catalog is a value containing the
admitted resource's hash and original SVG group locators. Its diagnostics report
invalid references independently of the pack's explicit coverage information.
The domain interprets Afreet's encoded label annotations and flag notation;
the generic media code does not interpret those names.

Palette bindings are maps from declared channel names to nonempty CSS property
strings. This slice checks colors, local paint references and opacity values;
the pure resolver merges them into effective plan bindings without recoloring art.

The committed SVG is a 250 KB text extraction from the historical Afreet
`paperdoll_shapes.forge.svg`, SHA-256
`3bab82e9077895b325c3e33c154e44a373e1d70a10eab7fdc68299d99ccb52ad`.
`resources/provenance.json` records the selected original parent and child IDs,
the source and subset hashes, and the extraction method. The SVG retains source
IDs, source ordering, parent attributes, 0 0 496 665 registration, geometry and
shading; no working layers or source master are included. No palette styles are
applied during indexing.

Coverage is deliberately narrow: a base common body, Toulouse hair, underwear and
camisole, with rose and blue palette choices. The historical common body's `top+a`
and its flag substitutions are omitted; the choices are a simplified selection,
not a claim of complete collection parity. Morphology variants, other body
models, rendering and a Look/outfit adapter remain explicit future work.
No unsupported choice changes character state or receives an invented fallback.

To audit a separately available historical SVG without adding it to this repo:

```sh
PYTHONPATH=engine/src:worlds/modiste_demo poetry run python -m modiste_demo.domain /path/to/source.svg
```

The report prints the source hash, viewBox, structural counts and integrity
diagnostic counts. CI uses only the committed subset and temporary SVG fixtures.

The world authority prepares its catalog from its own resource manager and reuses
it across journal reads. Accepted choices persist only the outfit and palette.
The resolved plan contains source references, ordered groups, effective bindings,
provenance and diagnostics; it contains no XML tree or live media resource. A
JSON-backed Service witness changes both choices, reopens the session and confirms
the same plan identity. This is P1, not assembled SVG delivery.

The media resolver canonicalizes declared aliases, applies ordered add, remove,
substitute and suppress operations, then sorts by declared layer with stable ties.
World-authored finite rules can require or exclude facts. Palette properties merge
from defaults through the selected palette to explicit overrides, with the source
of each property retained in the plan. Errors return diagnostics and no resolved
parts; a visual suppression never changes the original recipe.
