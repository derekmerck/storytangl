from tangl.narrative.dialog import DialogMuBlock
from tangl.media.images.staging_mu_block import StagingMuBlock
from .vox_spec import VoxSpec

class CueSheet:
    # Cue sheet maps voice to dialog and visual actor state/state changes

    vox_spec: VoxSpec

    dialog: list[DialogMuBlock]
    dialog_cues: list[float]  # Relative to vox start

    staged_media: list[StagingMuBlock]
    staged_media_cues: list[float]   # Relative to vox start
