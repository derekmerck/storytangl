from __future__ import annotations

from tangl.media.media_record import MediaRecord

class StableStage:
    model: str
    seed: int
    sampler: str
    iterations: int
    control_nets: list  # settings, ref ims
    ip_adapter: None    # settings, ref ims


class Auto1111Spec:

    prompt: str
    n_prompt: str
    stages: list[StableStage]
    ref_im: list[MediaRecord]


class Auto1111Adapter:

    def __init__(self, who, what, where, when, how,
                 spec_template: Auto1111Spec) -> Auto1111Spec:
        ...


# Implements MediaCreator
class Auto1111Creator:

    def create_media(self, spec: Auto1111Adapter) -> tuple[Auto111Spec, Image]:
        ...
