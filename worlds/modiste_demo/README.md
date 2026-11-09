# The Modiste's Catalogue

**Intent:** demonstrate world-scoped ingestion of a small Afreet-derived SVG
catalogue for the [Salon Season design](../../docs/src/world-designs/salon-season.md)
and [#661](https://github.com/derekmerck/storytangl/issues/661). Maintained witnesses
are `engine/tests/loaders/test_modiste_demo_world.py`,
`engine/tests/loaders/test_modiste_service.py`,
`engine/tests/loaders/test_modiste_region_export.py`, and the SVG forge tests
`test_svg_plan.py`, `test_vector_figure.py`, and `test_region_mask.py`. The story
delivers an assembled SVG figure alongside the textual plan, and optionally a
PNG derivative when the browser renderer is installed.

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
the pure resolver merges them into effective plan bindings. The world interprets
source annotations into explicit element targets; VectorForge applies the bindings
to those targets and preserves the source's registration, definitions and shading.
Shared ancestor IDs and compositing are retained. A requested order that would
split a shared ancestor is reported as an error.

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
models, general semantic masks and depth passes remain future work.
No unsupported choice changes character state or receives an invented fallback.

To audit a separately available historical SVG without adding it to this repo:

```sh
PYTHONPATH=engine/src:worlds/modiste_demo poetry run python -m modiste_demo.domain /path/to/source.svg
```

The report prints the source hash, viewBox, structural counts and integrity
diagnostic counts. CI uses only the committed subset and temporary SVG fixtures.

The world authority prepares its catalog from its own resource manager and reuses
it across journal reads. A template-materialized wearer owns an outfit and wardrobe;
accepted choices move the same graph-owned ensemble items and commit a whole-appearance
preset on the wearer's Look. The shared structured Look handoff feeds this world's
type-to-collection mapping, then the existing recipe and render plan prepare ordinary
media dependencies. Assignment slot, semantic body coverage, and artwork-derived
region masks are distinct: an item can occupy an upper slot while covering other
regions when it also covers the slot's region. The current outfit validator requires
that overlap; it does not yet support an upper-slot item covering legs alone.
Unsupported garment states and missing mappings return diagnostics without changing
the wearer to fit the artwork.
The resolved plan contains source references, ordered groups, effective bindings,
provenance and diagnostics; it contains no XML tree or live media resource. A
JSON-backed Service witness changes both choices, inspects the delivered SVG,
reopens the session and reuses an earlier figure. Rendering occurs at UPDATE;
journal and restore reads do not generate media. The optional PNG is a
496 x 665 transparent image, with the complete SVG viewBox centered and fit
without clipping or distortion. It renders the SVG in image mode with no active
or external content. Its identity includes the SVG content hash,
dimensions, background, fit, and Chromium and Playwright versions. If Chromium
is unavailable or fails, the SVG and text remain usable, and a later choice can
retry.

Install the optional package with `poetry install -E svg-png`, and provision
Playwright's Chromium separately with `poetry run playwright install chromium`.
No browser is downloaded by the engine. Ordinary engine tests do not require a
browser; run the fidelity and real Service witnesses explicitly with
`STORYTANGL_TEST_SVG_BROWSER=1 PYTHONPATH=engine/src poetry run pytest engine/tests/media/media_creators/svg_forge/test_svg_png.py engine/tests/media/media_creators/svg_forge/test_region_mask.py engine/tests/loaders/test_modiste_png_service.py engine/tests/loaders/test_modiste_region_export.py`.
Those tests check hard-light blending, gradient, clipping, opacity, transparent
padding, Service delivery and JSON recovery. The subset's own SVG annotations
and artwork determine its actual shading.

The **Export visible regions** choice explicitly creates lower-body and torso
mask PNGs, using world-owned group nominations and the current figure's layer
order. Each export records the source and beauty resource IDs, mask resource IDs,
viewBox, dimensions, contain fit, renderer and mask revisions, coverage status,
and absent depth. White denotes the region and black denotes other nominated
foreground; multiply the red channel by alpha for the mask value, including
anti-aliased edges. Missing selections are marked unrepresented, fully hidden
regions occluded, and incomplete group coverage partial. This is an opaque-fill
approximation: transparency, strokes, filters, stylesheet-driven geometry or
clipping, use/image/text and depth are reported as limits. Reading, restoration
and routine display do not generate masks.
The export rejects a selected palette channel with `fill:none` because that
paint would otherwise change coverage; the beauty figure remains available.
Per-region `visible_pixels` also records whether a partial pass has any visible
coverage, so an incomplete hidden pass remains distinguishable from a complete
occluded one.

The media resolver canonicalizes declared aliases, applies ordered add, remove,
substitute and suppress operations, then sorts by declared layer with stable ties.
World-authored finite rules can require or exclude facts. Palette properties merge
from defaults through the selected palette to explicit overrides, with the source
of each property retained in the plan. Errors return diagnostics and no resolved
parts; a visual suppression never changes the original recipe.
