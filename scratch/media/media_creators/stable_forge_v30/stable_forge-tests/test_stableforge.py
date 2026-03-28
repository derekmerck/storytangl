
from pprint import pprint

import pytest

from tangl.media.stableforge import Auto1111Spec, StableForge
from tangl.media.stableforge.auto1111_api import Auto1111Api
from tangl.config import settings

@pytest.mark.skipif("not settings.media.apis.stableforge.enabled")
@pytest.mark.xfail(raises=RuntimeError, reason="Cannot connect to auto worker")
def test_auto1111_api_txt2img():
    api = StableForge.get_auto1111_api()
    options = api.get_options()
    pprint( options )

    spec = Auto1111Spec(prompt="cinematic establishing shot of ornate dieselpunk grand central train station, spidertank legged walking mecha, steampunk great clock and travel board, busy, ww1 military outfits, style of maxfield parrish", n_prompt="bad worst lowres")

    im = api.generate_image(spec)
    if im:
        # im.show()
        print( im.info )

        # from tangl.media.stableforge.xmp_handler import XmpDataModel
        # xmp = XmpDataModel( **im.info )
        # pprint( xmp.xmp_tags )
        #
        # fp = "tmp.png"
        # im.save(fp=fp)
        # xmp.write_xmp(fp=fp)

