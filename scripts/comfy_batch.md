# ComfyUI one-off and batch helper

`comfy_batch.py` turns an API-format workflow template plus parameters and optional
local images into queued jobs. Submission returns immediately unless `--wait` is
given. It uses the existing `ComfyApi` transport but no `MediaSpec`, RIT,
provisioning, or worker-dispatcher lifecycle.

Run from the repository root in the project environment. In a source checkout
that is not installed, set `PYTHONPATH=engine/src` as shown below. The examples
use `/tmp` for receipts and downloaded images; choose durable storage for real work.
No SSH, server-local input paths, or new dependencies are required.

`--url` defaults to the first configured
`content.apis.stableforge.comfy_workers` entry. **There is no assumed default
host** — with nothing configured and no `--url`, the helper exits with an error
rather than guessing. A wrong host is no more useful than no host. Set it once
rather than passing one on every invocation; `settings.local.toml` is gitignored
and is the right place for a machine-specific worker:

```toml
dynaconf_merge = true

[content.apis.stableforge]
comfy_workers = ["http://your-worker:8188"]
```

`TANGL_`-prefixed environment variables and `.secrets.toml` also work. Pass
`--url` explicitly only to target a worker other than the configured one.

## First test: no models or source image

The included stock-node workflow generates a 64×64 solid color:

```sh
PYTHONPATH=engine/src poetry run python scripts/comfy_batch.py submit \
  scripts/examples/comfy/solid_color.json.j2 \
  --set color=3368652 \
  --receipts /tmp/comfy-toy/receipts.json \
  --wait --output-dir /tmp/comfy-toy/images
```

Add `--dry-run` to render/validate the workflow and save prepared receipts without
any network traffic. Re-run without `--dry-run` to submit those same requests.

For a model-free upload test, use `scripts/examples/comfy/image_passthrough.json.j2`
with `--image /path/to/source.webp` and a new receipt path. It loads and saves the
supplied image without a sampler. ComfyUI itself may re-encode it; the helper
preserves the exact bytes it uploads and downloads.

## Workflow templates

Export **API-format JSON** from ComfyUI, not the UI layout JSON containing
`nodes` and `links`. Keep its actual graph, models, samplers and output nodes.
Replace only the input values you want to expose with Jinja expressions:

```jinja
"text": {{ prompt | tojson }}
"noise_seed": {{ seed }}
"image": {{ images.source | tojson }}
```

Use `tojson` **without surrounding quotes** for strings: it safely handles quotes,
newlines, backslashes, and Unicode in prompts. A template is consequently usually
named `workflow.json.j2`; it becomes valid JSON after rendering. Numbers remain
numbers. Undefined variables fail before any upload or dispatch. Supplied prompt
strings are data, not recursively evaluated templates.

Composing a short style directive directly in the workflow works too:

```jinja
"text": {{ ("Render subject with " ~ style
  ~ (", vague background" if focused else "")
  ~ (", generic cartoon faces" if semi_anon else "")) | tojson }}
```

Supply these with `--set style='loose ink and wash, watercolor blooms'`,
`--set focused=true`, and `--set semi_anon=false`. `--set` values are parsed as JSON
when possible, otherwise as strings. No particular positive/negative prompt node,
model family, seed node, or negative conditioning path is assumed.

Use normalized, correctly oriented WebP sources when appropriate. Uploads preserve
the original supplied bytes: this helper does not rotate, resample, caption,
anonymize, or otherwise preprocess them.

## One job or a small Cartesian product

```sh
PYTHONPATH=engine/src poetry run python scripts/comfy_batch.py submit \
  /path/to/restyle.json.j2 \
  --prompt 'Render subject with loose ink and wash, watercolor blooms.' \
  --prompt 'Render subject with loose ink and wash, watercolor blooms, vague background.' \
  --image /path/to/one.webp --image /path/to/two.webp \
  --seed 910 --seed 911 \
  --receipts /tmp/comfy-restyle/receipts.json
```

This queues eight jobs: prompts × images × seeds. Each `--image` is a separate
job source, bound as `images.source`. Omitted dimensions contribute one job,
not zero. There are no hidden random seeds or seed increments: either supply
`--seed`, supply a parameter in the manifest, or leave a concrete seed in the
workflow. Exact duplicate concrete requests collapse to one job.

Without `--wait`, submission ends after receiving job IDs. To poll once or wait
later, in another process:

```sh
PYTHONPATH=engine/src poetry run python scripts/comfy_batch.py collect \
  /tmp/comfy-restyle/receipts.json

PYTHONPATH=engine/src poetry run python scripts/comfy_batch.py collect \
  /tmp/comfy-restyle/receipts.json \
  --wait --timeout 28800 --output-dir /tmp/comfy-restyle/images
```

`--output-dir` downloads completed image outputs. Without `--wait` it performs one
collection pass; pending jobs remain pending. Collection polls every submitted job
each pass, so a slow first job does not prevent collecting later completions.

Collection rejects receipts containing unsubmitted (`prepared`) jobs, even alongside
completed jobs. After a dry run, rerun the original `submit`/`batch` command without
`--dry-run`, using the same receipt path. `collect` never submits jobs itself.

## Explicit batch: different parameters or several images per job

Create a manifest such as:

```json
{
  "workflow": "restyle.json.j2",
  "params": {"style": "loose ink and wash, watercolor blooms", "focused": true},
  "jobs": [
    {
      "params": {"seed": 910, "semi_anon": false},
      "images": {"source": "media/castle.webp", "reference": "media/style-guide.webp"}
    },
    {
      "params": {"seed": 911, "semi_anon": true},
      "images": {"source": "media/portrait.webp", "reference": "media/style-guide.webp"}
    }
  ]
}
```

Use `images.source` and `images.reference` in the corresponding LoadImage nodes.
Workflow and source paths resolve **relative to the manifest**, not the shell's
working directory. Job parameters override batch defaults; `images` is reserved.

```sh
PYTHONPATH=engine/src poetry run python scripts/comfy_batch.py batch /path/to/jobs.json \
  --receipts /tmp/comfy-explicit/receipts.json --wait
```

No matrix language is added to manifests: callers can mechanically generate the
explicit jobs list when they need more elaborate experiments.

## Recovering a workflow from a ComfyUI PNG

ComfyUI writes the graph into PNG `tEXt` chunks, so a generated image usually
carries the workflow that made it. Prefer recovering a known-good workflow over
authoring one:

```sh
PYTHONPATH=engine/src python scripts/workflow_from_png.py <image.png> --models -o out.json
```

It exports the literal API JSON and prints model dependencies plus a
**non-exhaustive** list of candidate parameters. It does not parameterize
anything for you, and its suggestions key on common input names, so knobs such as
`cfg` and `denoise` will be missed — read the exported graph.

Two chunks may be present. `prompt` is API format and is what this helper
consumes; `workflow` is the canvas layout and only appears on UI-generated
images, for loading back into ComfyUI.

This is **workflow recovery, not a reproduction guarantee.** The metadata carries
the graph only — not source-image bytes, model weights, ComfyUI or torch
versions, or the GPU. Any of those changing can change the output. Metadata is
also fragile: screenshots, chat uploads, and most editors strip it. An extracted
workflow additionally names uploaded sources by their content-addressed server
filename, which depends on server state; replace that with
`{{ images.source | tojson }}` and pass `--image` so the helper re-uploads.

## Bundled example workflows

`scripts/examples/comfy/` holds the model-free smoke templates plus Flux.2 Klein
scene templates:

| Template | Shape |
| --- | --- |
| `solid_color.json.j2` | stock nodes, no models — first connectivity test |
| `image_passthrough.json.j2` | upload round trip, no sampler |
| `flux2_klein.json.j2` | Flux.2 Klein text-to-image |
| `flux2_klein_ref.json.j2` | plus `FluxKontextImageScale` reference conditioning |
| `flux2_ref_scene.json.j2` | `ReferenceLatent` conditioning, explicit output dimensions |
| `flux2_ref_img2img.json.j2` | **experimental** — reference latent seeds the sampler via `SplitSigmasDenoise` |

The Flux.2 templates name specific model files; query `/object_info` on the
target worker rather than assuming they exist there.

Two notes learned the hard way. A workflow that wires `GetImageSize` from a
scaled reference into the latent and scheduler **inherits its output aspect ratio
from that reference**, which silently produces mismatched sizes across a set;
`flux2_ref_scene.json.j2` takes explicit `width`/`height` instead. And exported
UI graphs often carry orphaned nodes and a `PreviewImage` whose output is temp —
drop the orphans and use `SaveImage` with a `filename_prefix` when templatizing.

`denoise` in the img2img template is quantized against `steps`, so its useful
range moves with the step count. Sweep it for your own step count with a batch
manifest rather than trusting a fixed table.

## Bookkeeping and failure semantics

- Receipts include the template, parameters, source paths and byte SHA-256 hashes,
  pre-upload concrete workflow, actual submitted workflow, prompt IDs, status,
  full worker history, and optional downloaded paths/hashes.
- Request identity hashes the concrete workflow plus source-slot hashes, not local
  source paths. A rename with the same extension and bytes does not change identity.
  The endpoint is separately bound to the receipt so it cannot be resumed against
  the wrong worker. This is a request fingerprint, not a fingerprint of installed
  model weights, custom nodes, or the worker environment.
- Inputs use content-addressed upload names. Identical sources are uploaded once
  per submission process; the server's returned name/subfolder is used even if it
  differs. Sources are rehashed before upload to detect changed input bytes.
- Re-running the same submit/batch command with the same receipt skips previously
  submitted jobs. Another batch or worker requires another receipt path. One process
  owns each receipt: there is no concurrent scheduler, lock service or distributed
  exactly-once claim.
- Before each POST the receipt is marked `submitting`. A lost acknowledgement leaves
  `submission_unknown` (or `submitting` after process interruption). Such jobs are
  **not automatically retried**. Inspect `/queue` and `/history` on that worker;
  after confirming a matching job, record its `prompt_id` and `submitted` status in
  the receipt. Reset to `prepared` only after confirming it was not accepted.
  Explicit validation rejection is `rejected`; remote execution failure/interruption
  is `failed`. Neither silently rerenders. Use a new receipt for an intentional retry.
- Completed history is required for completion; partial preview images are not
  sufficient. Empty or non-image outputs can still complete successfully, with raw
  outputs retained in history. Automatic downloading currently handles only the
  standard `images` output references; audio/video/custom outputs stay in history.
- Downloads preserve bytes and embedded PNG metadata. They go into request-hash
  subdirectories, with indexed server basenames, and will not overwrite differing
  local content. Media downloads inside this repository are rejected for LFS safety.
- Wait expiry and Ctrl-C do not cancel jobs. Collection can resume using the receipt.
  If the worker clears history or restarts, a job with no history remains unresolved;
  absence is not treated as permission to render again.
- `--timeout` is the collection wait budget, checked between polling passes.
  `--http-timeout` bounds each network request (default 30 seconds), so a poll pass
  may extend beyond the wait budget. `--poll-interval` defaults to 2 seconds.
- Exit codes: `0` successful submission/collection pass; `1` input, network,
  submission or execution error; `2` wait budget expired; `130` interrupted.
  A successful nonblocking submission does not claim successful rendering.

The Python seams are `prepare_jobs`, `submit_jobs`, and `collect_jobs`.
Their small JSON receipts are the handoff surface for a future backend job type;
they are not graph persistence and do not yet create inventory entries. A later
forge adapter can bind these receipts to its own resource/job lifecycle without
putting narrative concepts into this helper.

The HTTP endpoints follow the upstream [ComfyUI server implementation](https://github.com/Comfy-Org/ComfyUI/blob/master/server.py).
