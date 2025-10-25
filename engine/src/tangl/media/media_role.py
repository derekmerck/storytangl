from __future__ import annotations
from enum import Enum


class MediaRole(Enum):

    IMAGE = "image"
    # formats: generic raster (png) or vector (svg)

    NARRATIVE_IM   = "narrative_im"

    # size hints: landscape, portrait, square
    NARRATIVE_IM_L = "narrative_im_landscape"
    NARRATIVE_IM_P = "narrative_im_portrait"
    NARRATIVE_IM_S = "narrative_im_square"

    AVATAR_IM = "avatar_im"        # portrait, dynamic svg, has actor look
    DIALOG_IM = "dialog_im"        # sm square, dynamic, has actor attitude

    INFO_IM = "info_im"            # landscape, used in ui info overlays
    LOGO_IM = "logo_im"            # sm square, used in nav bar/branding

    COVER_IM = "cover_im"          # e-pub cover with title

    # --------------

    AUDIO = "audio"
    # formats: mp3

    NARRATIVE_VOX = "narrative_vox"  # for common narration
    CHARACTER_VOX = "character_vox"  # for dialog, has actor, attitude

    MUSIC = "music"     # soundtrack audio
    SFX   = "sound_fx"

    # --------------

    VIDEO = "video"
    # formats: mp4
    ANIMATION = "animation"

    # --------------

    EXTRA = "extra"                # everything else
