# StableForge

This package contains the partial Stable Diffusion media-spec vocabulary and an
Automatic1111 adapter. ``StableSpec`` remains the shared base used by the Comfy
adapter; the Automatic1111 execution path is retained as an experimental
backend and is not a supported production workflow.

Current boundaries:

- ``StableSpec`` describes prompts, seed, sampler, dimensions, and optional
  image-to-image inputs.
- ``Auto1111Spec`` adds Automatic1111-specific reference controls.
- ``StableForge`` selects the first configured ``auto1111_workers`` endpoint.
- Worker configuration owns checkpoint/model selection; requests do not switch
  the active model.
- Shot-list expansion, XMP review workflows, output watchers, and model-farm
  scheduling belong only to the retired v3.0 scratch prototype.

The broader media lifecycle and forge-selection contracts are documented in
``tangl/media/MEDIA_DESIGN.md`` and tracked by issue #284.
