from tangl.media.illustrated.stableforge.auto1111_api import Auto1111Api as WebUIApi
from tangl.media.illustrated.stableforge.stableforge_specs import Auto1111Spec as StableForgeSpec
from tangl.config import settings

import pytest

@pytest.mark.skipif(not settings.apis.stableforge.enabled, reason='stableforge disabled')
def test_get_api():
    print( settings.apis.stableforge.auto1111_workers[0] )
    api = WebUIApi( settings.apis.stableforge.auto1111_workers[0] )
    print( api )

@pytest.mark.skipif(not settings.apis.stableforge.enabled, reason='stableforge disabled')
def test_basic_txt2img():

    api = WebUIApi( settings.apis.stableforge.auto1111_workers[0] )
    s = StableForgeSpec(prompt="a boat")
    img = api.generate_image(s)  # type: Image
    assert img is not None
    print( img.size )
    if s.hr_fix:
        assert img.size == (768, 768)
    else:
        assert img.size == (512, 512)
    # img.show()

@pytest.mark.skipif(not settings.apis.stableforge.enabled, reason='stableforge disabled')
def test_hi_res_txt2img():
    api = WebUIApi( settings.stableforge.workers[0] )
    s = StableForgeSpec(prompt="a boat",
                        model_hash="deliberate2",
                        hires_fix={'scale': 2.0}
                       )
    img = api.txt2img(s)  # type: Image
    assert img is not None
    # img.show()
    print( img.size )
    assert img.size == (640, 640)
