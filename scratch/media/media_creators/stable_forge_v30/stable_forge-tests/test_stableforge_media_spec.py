import pytest
from PIL import Image
from tangl.media.illustrated.stableforge.stableforge_specs import Auto1111Spec as StableForgeSpec
# from tangl.media.illustrated.stableforge.hash2model import ModelHashes
from tangl.media.illustrated.stableforge.parse_info import parse_info

def test_StableForgeSpec_init():
    spec = StableForgeSpec(prompt='a sailboat', n_prompt='lowres blur anime cg 3d')
    #
    # # Check uid is correctly set
    # assert spec.uid == 'test_uid'

    # Check default values
    assert spec.prompt == "a sailboat"
    assert spec.n_prompt == "lowres blur anime cg 3d"
    # assert spec.model_hash == ModelHashes.model_to_hash("sd15")
    assert spec.seed is None
    assert spec.cfg_scale == 4.5
    assert spec.sampler is None
    assert spec.steps is None
    # assert spec.dims == (320, 320)
    # assert spec.hires_fix is None
    # assert spec.img2img is None
    # assert spec.ctrlnet is None
    # assert spec.meta == {}

def test_StableForgeSpec_HiresFixSpec():
    hires_fix = StableForgeSpec.HiresFixSpec(scale=2.0, denoise=0.5)
    assert hires_fix.scale == 2.0
    assert hires_fix.denoise == 0.5

def test_StableForgeSpec_Img2ImgSpec():
    img = Image.new('RGB', (60, 30), color = (73, 109, 137))
    img2img = StableForgeSpec.Img2ImgSpec(image=img, denoise=0.5)
    assert img2img.image == img
    assert img2img.denoise == 0.5

def test_StableForgeSpec_CtrlNetSpec():
    img = Image.new('RGB', (60, 30), color = (73, 109, 137))
    ctrlnet = StableForgeSpec.CtrlNetSpec(image=img, processor='canny', model_name='canny', weight=1.0, guidance=1.0, guidance_start=0.0, guidance_end=1.0, processor_res=512)
    assert ctrlnet.image == img
    assert ctrlnet.processor == 'canny'
    assert ctrlnet.model_name == 'canny'
    assert ctrlnet.weight == 1.0
    assert ctrlnet.guidance == 1.0
    assert ctrlnet.guidance_start == 0.0
    assert ctrlnet.guidance_end == 1.0
    assert ctrlnet.processor_res == 512

def test_parse_info():
    info = \
        'pretty aria the bard, purple lips, lavender eyes, long legs, ' \
        'ponytail hair, (((classical japanese ink brush and woodblock ' \
        'art scroll)))\n' \
        'Steps: 20, Sampler: Euler a, CFG scale: 7, Seed: 2286316612, ' \
        'Size: 512x512'

    kwargs = parse_info(info)
    print( kwargs )
    spec = StableForgeSpec( **kwargs )
    assert isinstance(spec, StableForgeSpec)
    print( spec )

@pytest.mark.xfail(raises=NotImplementedError)
def test_StableForgeSpec_from_xmp():
    data = {'uid': 'test_uid'}
    spec = StableForgeSpec.from_xmp(data)
    assert isinstance(spec, StableForgeSpec)
    assert spec.uid == 'test_uid'

    duplicate_spec = StableForgeSpec(
                    uid='test_uid2',
                    prompt='pretty aria the bard, purple lips, lavender eyes, long legs, ponytail hair, (((classical japanese ink brush and woodblock art scroll)))',
                    neg_prompt=None, model_hash=None, seed=8626136927192645476, cfg_scale=4.5, sampler='Euler a',
                    steps=20, dims=('512', '512'), hires_fix=None, img2img=None, ctrlnet=None,
                    meta={'actors': ['aria the bard']})

    assert spec.digest == duplicate_spec.digest
    assert spec == duplicate_spec

    non_duplicate_spec = StableForgeSpec(uid='test_uid3')
    assert spec.digest != non_duplicate_spec.digest
