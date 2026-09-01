---
name: storytangl-comfy-batch
description: Prepare, submit, resume, and collect ComfyUI one-off or batch jobs using StoryTangl's scripts/comfy_batch.py. Use for templated workflow JSON, prompt/image/seed variants, source uploads, and receipt-based queue attendance; not for unrelated image generation or deploying GPU services.
---

# StoryTangl ComfyUI jobs

Use the maintained helper, not a fresh HTTP submission loop. Resolve paths from
the current StoryTangl checkout, not a remembered home directory or another
worktree. The helper deliberately bypasses MediaSpec/RIT provisioning; do not
introduce forge integration merely to execute a batch.

## Ground the request

Read [the helper usage guide](../../../scripts/comfy_batch.md) before preparing
commands. It owns the manifest schema, CLI flags, and receipt semantics. Inspect
[the implementation](../../../scripts/comfy_batch.py) for behavior not covered
there, debugging, or requested changes.

- Establish the workflow, parameters/variants, optional sources, receipt location,
  and whether the user wants submission only or collected output. The worker URL
  comes from `content.apis.stableforge.comfy_workers` via
  `configured_comfy_url()`; `--url` defaults to it, so omit the flag unless
  overriding. Never hard-code a host. There is no assumed default: with nothing
  configured the helper errors rather than trying localhost, so ask the user for
  a URL instead of guessing one. Do not assume a model inventory or previous
  host availability — query `/object_info` on the target worker.
- To reuse or replay an existing image's graph, recover it with
  `scripts/workflow_from_png.py`; see the helper guide's recovery section for what
  the metadata does and does not carry. Bundled example workflows, including
  model-free smoke templates, live in `scripts/examples/comfy/`.
- Run from the repository root in its existing Python environment. The documented
  command is `PYTHONPATH=engine/src poetry run python scripts/comfy_batch.py ...`.
  If Poetry selects an incomplete environment, use a verified existing project
  interpreter with the same source path. Do not hard-code another checkout's venv.
- Preparing templates, manifests, or a skill is not authorization to upload images
  or consume worker resources. Respect the requested operation and tool permissions.
  Installing models, restarting containers, or changing worker configuration is
  separate work.

## Choose the input shape

| Request | Helper mode |
| --- | --- |
| One job or prompts × source images × seeds | `submit workflow.json.j2` |
| Per-job parameters or several images in one job | `batch jobs.json` |
| Existing prompt IDs and receipts | `collect receipts.json` |

Repeated `--image` values in `submit` produce separate jobs; they are **not** multiple
inputs to the same job. Use a manifest's named `images` map for that. Manifest
workflow/source paths are relative to the manifest. CLI paths are relative to cwd.
Exact concrete duplicates collapse; count the prepared receipts before dispatch.

## Prepare the workflow

Start with the user's working **API-format** node graph, not the UI layout export.
Preserve model names, connections, conditioning, and sampler settings unless the
user requests a change. Expose only the knobs the task needs:

```jinja
"text": {{ prompt | tojson }}
"noise_seed": {{ seed }}
"image": {{ images.source | tojson }}
```

String expressions using `tojson` have no surrounding quotes. Supplied prompt
strings are data, not a second layer of Jinja. Use explicit seeds or the workflow's
concrete seed; the helper does not randomize them. `images` is a reserved namespace.
Do not assume a negative prompt is connected or useful in every workflow.

Uploads preserve supplied bytes. Prefer a known correctly oriented derivative when
raw scan metadata is unreliable; the helper does not fix orientation, resample,
caption, or anonymize. Generic-face prompting is not verified anonymization.

For a new or changed batch, use `--dry-run` first and inspect the rendered nodes,
source hashes, seeds, and deduplicated job count. This saves prepared receipts with
no network requests. For a model-free offline example, from the repo root:

```sh
batch_dir=$(mktemp -d /tmp/storytangl-comfy.XXXXXX)
PYTHONPATH=engine/src poetry run python scripts/comfy_batch.py submit \
  scripts/examples/comfy/solid_color.json.j2 \
  --receipts "$batch_dir/receipts.json" --dry-run
```

The [solid-color template](../../../scripts/examples/comfy/solid_color.json.j2) needs
no model. The [image-passthrough template](../../../scripts/examples/comfy/image_passthrough.json.j2)
tests source upload with `--image`. Live smoke tests still submit real worker jobs;
do not run them merely to validate documentation.

## Dispatch, wait, and recover

- Once live submission is in scope, remove `--dry-run` from the prepared command,
  retaining its URL, inputs, and receipt path. Default submission returns job IDs.
  Use `--wait` for foreground polling or `collect` later without resubmission.
- Use durable receipt/output storage for real batches. Downloads must be outside
  the StoryTangl repository. One process owns each receipt file; this is not a
  multi-worker scheduler or background monitoring service.
- On a normal resume, keep the original receipt: already submitted jobs are skipped.
  A filename change with the same bytes and extension does not create a new request.
  Do not discard a receipt simply because an image has been renamed.
- On `submitting` or `submission_unknown`, stop submission and reconcile with that
  worker's queue/history. A POST timeout may mean the job was accepted. Never reset
  these statuses or choose a fresh receipt just to bypass duplicate protection.
  If acceptance cannot be determined, report the uncertainty and ask before retrying.
- A wait timeout or Ctrl-C does not cancel remote jobs. Collect again with the same
  receipt. Missing history after a restart is unresolved, not permission to rerender.
  `failed` and `rejected` are terminal; deliberate retries need a new receipt and
  must remain within the user's requested retry/sample budget.
- HTTP/collection errors are reported, not silently retried indefinitely. Inspect
  the receipt before deciding the next action; never interrupt the entire worker
  to recover one job without authorization.

## Verify and hand off

Inspect receipt statuses rather than treating queue acceptance as rendering success.
Report the receipt path, job counts/statuses, failures or unresolved IDs, and any
download location. `--output-dir` fetches standard image references only; other
output types remain in raw history. Preserve output bytes/PNG metadata and hashes.
Request fingerprints do not pin installed model weights or custom-node versions.

Exit codes: `0` successful submission/collection pass, `1` error, `2` wait expired,
`130` interrupted. For requested helper changes, run the offline suites that ordinary
CI discovers:

```sh
PYTHONPATH=engine/src poetry run pytest \
  scripts/tests \
  engine/tests/media/media_creators/comfy_forge \
  engine/tests/media/test_comfy_forge.py
```

`scripts/tests` owns the standalone helper, bundled templates, and PNG recovery
contracts and refuses network access even when local worker settings exist. The
engine paths own Comfy forge/spec/dispatcher behavior; their one real-worker test is
collected but skipped unless `RUN_COMFY_INTEGRATION=1`. Run that opt-in test only when
live rendering is authorized, using `COMFY_URL` or configured worker settings and an
optional `COMFY_TEST_CHECKPOINT`. `scripts/comfy_smoke_test.py` is a separately invoked
manual diagnostic, not a pytest suite. Do not rewrite the helper for ordinary dispatch
or duplicate its manual in this skill.
