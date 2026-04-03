# StableForge

<!--- todo: needs revision -->

StableForge wraps the Python [webuiapi][] package, which is itself a wrapper for the Automatic1111 fork of the [stable-diffusion-webui][] api.

[webuiapi]: https://github.com/mix1009/sdwebuiapi
[stable-diffusion-webui]: https://github.com/AUTOMATIC1111/stable-diffusion-webui

StableForge supports:

- juggling multiple apis running different models
- "shot-lists", a mini-DSM for creating stable-diffusion jobs ('StableforgeSpecs')
- managing a cache of rendered job-outputs
- XMP format tagging for reviewing images with tools such as [Adobe LightRoom][]

[Adobe Lightroom]: https://www.adobe.com/products/photoshop-lightroom.html

## Basic Usage

1. Compute shot-list specs from scripts
2. Load the shot-list specs and expand multi-params (i.e., long hair/short hair)
3. Setup _n_ api's with specific model responsibilities
4. Compute as many shots from the shot-list as possible given the models available
5. XMP tag and save images
6. Reset api's with new models and continue

Consider multi-stage models, for example, where we might use various models for initial rendering with euler_a (fast), then `protogen58` with `dpm_sde_keras` (slow) as a final pass low-denoise `img2img` upscale on all of them to consolidate look/feel.

## Scripts

`annotate-images` Compute and optionally xmp tags for an Auto1111-generated image.

## Watcher

(TBD, `annotate-images -d`)

A StableForge daemon can watch output folders for 1-off images and review tags.

1-offs will be automatically retagged and sorted into review folders.

Review flags are interpreted as:

- 5 = as is
- 4 = req work
- 3 = consider
- 2 = poor
- 1 = reject

Save and rename current 5's to media folder
Save and rename current 4's to work folder

## Automatic1111 API

Manually starting up Auto1111 with api support.

```bash
$ python webui.py --listen --enable-insecure-extension-access --disable-safe-unpickle --xformers --api
```

## StoryTangl Dependencies

StableForge is _nearly_ independent of the StoryTangl code base, but it does rely on common utilities like `tangl.utils.expand_configs` and settings.  

Moreover, the "shotlist" parser assumes `roles` and `locs` indirect variables, following the tangl.scene attribute notation.
