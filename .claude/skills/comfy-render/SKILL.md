---
name: comfy-render
description: Render images on the project's local ComfyUI server via scripts/comfy_batch.py. Use when asked to generate, mock up, restyle, or iterate on game art, sprites, backgrounds, textures, portraits, or UI assets — including reference-image conditioning. Also use when asked what models the render node has, to re-run/collect a previous render batch, or to read, recover, or reuse the workflow embedded in a ComfyUI-generated PNG.
---

# ComfyUI rendering

`scripts/comfy_batch.py` submits templated API-format workflows to a ComfyUI
worker. It uses the engine's `ComfyApi` transport but no `MediaSpec`, RIT, or
provisioning lifecycle — it is a plain job runner with JSON receipts.

Read `scripts/comfy_batch.md` for the full contract. This skill covers the
working invocation, two ready templates, and the traps.

Read [the helper usage guide](../../../scripts/comfy_batch.md) first — it owns
the manifest schema, CLI flags, receipt semantics, PNG recovery, and the bundled
example workflows. This skill adds only the render-loop habits on top.

## Server

The endpoint comes from settings, never from a hardcoded host. `comfy_batch.py`
reads it automatically, so **omit `--url`** unless targeting a different worker.

```bash
COMFY=$(PYTHONPATH=engine/src python -c "from tangl.media.media_creators.comfy_forge._common import configured_comfy_url; print(configured_comfy_url() or '')")
```

If that comes back empty, no worker is configured. Say so rather than guessing a
host — `settings.local.toml` is gitignored and is where a machine-specific
worker belongs:

```toml
dynaconf_merge = true

[content.apis.stableforge]
comfy_workers = ["http://your-worker:8188"]
```

Check the worker is up before doing anything else:

```bash
curl -s -m 5 "$COMFY/system_stats"
```

Query what is installed rather than guessing model names:

```bash
curl -s "$COMFY/object_info/UNETLoader" | python3 -c "import json,sys; d=json.load(sys.stdin); print([v['input']['required']['unet_name'][0] for v in d.values()])"
```

Verified present on the worker used to build this skill: UNET
`flux-2-klein-4b-fp8.safetensors`, CLIP `qwen_3_4b.safetensors` (type `flux2`),
VAE `flux2-vae.safetensors`, plus SDXL, SD1.5, Pony, Illustrious, and
Flux1-dev-Kontext checkpoints. Another worker may differ — query, do not assume.

## Invocation

Run from the repo root. Inside a git worktree `poetry run` fails, because the
environment is keyed to the main checkout — resolve the interpreter once and
reuse it:

```bash
PY=$(poetry env info --executable 2>/dev/null || command -v python3)
```

```bash
PYTHONPATH=engine/src "$PY" scripts/comfy_batch.py submit <template.json.j2> \
  --prompt "..." \
  --set width=1280 --set height=800 --set steps=4 --set cfg=1 --set prefix=name \
  --seed 7 \
  --receipts <scratch>/receipts.json \
  --wait --timeout 600 --output-dir <scratch>/images
```

`--url` is omitted deliberately; see **Server** above. Write receipts and images
to a scratch directory — downloads into the repo are rejected for LFS safety.

Then `Read` the returned PNG path to actually look at the result. Never report a
render as good without viewing it.

## Templates

Both live beside this file and are verified working against the live worker.

**`flux2_ref_scene.json.j2`** — *the one to reach for.* Derived from the tuned
harbour workflow. `ReferenceLatent` conditioning + `CFGGuider`, with output
dimensions **explicit** rather than inherited from the reference.
Params: `prompt`, `width`, `height`, `steps`, `cfg`, `seed`, `prefix`, `--image`.
Known-good: `steps=4`, `cfg=1` at 1280×800. Klein is heavily distilled — 4 steps
is the tuned value for scene work, not a placeholder. Composes a **new** scene;
the reference contributes loose stylistic influence only.

**`flux2_ref_img2img.json.j2`** — **EXPERIMENTAL.** Same graph, but the
reference latent seeds the sampler through `SplitSigmasDenoise`, so the source
composition is preserved and restyled rather than replaced. Adds `denoise`.

`denoise` is **quantized against `steps`**, so its useful range moves with the
step count and there is no portable calibration table. Observed on this worker,
same seed, one source image, one sample per value:

- at `steps=12`: 0.65 left the source almost untouched, 0.90 read as the source
  hand-coloured, 0.95-0.99 gave a full palette restyle.
- at `steps=4`: 0.90 already gives the full restyle. Three values across
  0.90-0.99 produced three distinct outputs, so the knob is live at low step
  counts, but the thresholds are not the ones above.

Treat those as anecdotes, not calibration. **Sweep `denoise` at your own step
count** — `comfy_batch` batch manifests exist for exactly this — and look at the
results. Reference conditioning also influences composition on its own, so
neither workflow *guarantees* preservation; it is a strong tendency, not a
contract. The source's frame, caption band, and borders survive as structure, so
crop the reference first.


**`scripts/examples/comfy/flux2_klein*.json.j2`** — minimal hand-built
txt2img and `FluxKontextImageScale` reference variants. Kept as small
smoke-tests; prefer `flux2_ref_scene` for real work.

For anything else, export **API-format JSON** from the ComfyUI UI (not the layout
JSON with `nodes`/`links`), then replace only the inputs you want to expose with
Jinja: `{{ prompt | tojson }}`, `{{ seed }}`, `{{ images.source | tojson }}`. Use
`tojson` *without* surrounding quotes for strings.

## Recovering a workflow from a ComfyUI PNG

ComfyUI embeds the workflow in PNG `tEXt` chunks, so a generated image usually
carries the graph that made it. This is **workflow recovery**, not a
reproduction guarantee. **Prefer recovering a known-good workflow over authoring
one.**

```bash
PYTHONPATH=engine/src "$PY" \
  scripts/workflow_from_png.py <image.png> --models -o out.json.j2
```

It exports the literal JSON and prints model dependencies plus a
**non-exhaustive** list of candidate parameters — it does not parameterize
anything for you. The suggestion list keys on common input names and will miss
knobs like `cfg` and `denoise`, so read the exported graph rather than trusting
it. Replace values with Jinja by hand to get a template.

Two chunks exist:

- **`prompt`** — API format. Exactly what `comfy_batch.py` consumes. Present on
  anything ComfyUI generated.
- **`workflow`** — canvas layout. Only on UI-generated images; load it back into
  the ComfyUI canvas, not into this helper.

**On reproducibility.** In one observed experiment, recovering a workflow and
resubmitting it verbatim against the same worker minutes later reproduced a
byte-identical PNG, and `comfy_batch` recognized it as the same request
fingerprint. That is evidence the sampler is deterministic given an unchanged
environment — it is **not** a general contract. The metadata carries the graph
only: not source-image bytes, not model weights, not ComfyUI or torch versions,
not the GPU. Any of those changing can change the output. Say "recovered the
workflow", not "reproducible".

Caveats:

- **Metadata is fragile.** Screenshots, chat/messaging uploads, and most editors
  strip `tEXt`. If an image arrives without a `prompt` chunk, ask for the original
  file off disk rather than a pasted or re-encoded copy.
- **Baked image references go stale.** An extracted workflow names uploaded
  sources by their content-addressed server filename. Replace that with
  `{{ images.source | tojson }}` and pass `--image`, so the helper re-uploads and
  rebinds instead of depending on server state.
- Reproducibility is bounded by the worker: same models, custom nodes, and
  ComfyUI version. The request hash fingerprints the workflow, not the environment.

## Traps

- **Always `--dry-run` a new or edited template first.** It renders and validates
  the workflow with zero network traffic.
- **One process owns each receipt.** Re-running the same command with the same
  receipt path skips already-submitted jobs — that is resume, not retry. A new
  batch needs a new receipt path.
- **Never download into the repository.** Media downloads inside the repo are
  rejected for LFS safety. Use the session scratchpad.
- **`--prompt`/`--image`/`--seed` multiply.** Three prompts × two images × two
  seeds queues twelve jobs. Omitted dimensions contribute one, not zero.
- Submission without `--wait` returns as soon as job IDs come back; use
  `collect <receipts.json> --wait --output-dir ...` from any process to finish.
- A failed or interrupted job is **not** auto-retried, and absence of history is
  not permission to re-render. Inspect `/queue` and `/history` on the worker.
- **Output aspect ratio is inherited from the reference** in any workflow that
  wires `GetImageSize` into the latent and scheduler — which is how a set of
  backgrounds silently ends up at mismatched ratios. `flux2_ref_scene` takes
  explicit `width`/`height` instead. Keep `ImageScaleToTotalPixels` for
  normalizing the *input*.
- `collect` takes no `--url`; the endpoint is bound to the receipt.
- Exported UI workflows often carry **orphaned nodes** (a spare `CLIPTextEncode`
  from a style experiment) and use `PreviewImage`, whose outputs are temp. Drop
  the orphans and swap in `SaveImage` with a `filename_prefix` when templatizing.
- A cream border/frame is a persistent habit of this model at scene prompts. Add
  `full bleed, image fills the canvas edge to edge, no border, no frame`, and
  check the output — it may still need a crop.

## House style for this project's game art

The repartee/Sierra demo assets share a style block. Append to prompts:

```
render scene with 8-bit dithered palette style, limited palette of muted
teal, weathered sand, rust orange, bone cream, deep indigo; ordered Bayer
dither for all gradients; crisp readable silhouettes; flat lighting;
no text, no lettering, no watermark, no signature
```

- Backgrounds: add `full bleed, image fills the canvas edge to edge, no border,
  no frame` and `no people, empty center staging area` — sprites composite on top.
- Sprites: `flat pure magenta #FF00FF background, no shadow, no ground plane`,
  and `entire figure and all props contained within the frame, feet at the
  bottom edge`. Magenta is asked for because it is outside the palette, but the
  model will not hold it exactly — expect to key with tolerance, or use `rembg`,
  and check edges rather than assuming a clean cut.
- UI frames: `perfectly symmetrical and orthogonal, no perspective`. This makes
  a 9-sliceable result *more likely*, not guaranteed; verify the corners and
  straight edges before slicing, and expect to redraw borders by hand.
- With a strong reference image, keep the prompt to **costume and palette deltas**
  and let the image carry pose and silhouette. A specific prompt overrides the
  reference; a dense reference (fine-hatched panoramas) conditions poorly, while a
  single high-contrast subject on blank ground conditions well.
