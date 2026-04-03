from pathlib import Path

import yaml
from PIL import Image

from tangl.config import settings

from tangl.world.illustrator.stableforge.sd_spec import StableSpec
from tangl.world.illustrator.stableforge.webuiapi import WebUIApi
from tangl.world.illustrator.stableforge.spec2xmp import write_xmp, write_xmp_sidecar
from tangl.world.illustrator.stableforge import StableForge

import pytest

def test_create_spec():
    s = StableSpec(uid="test", prompt="a boat", seed=1, model_hash="deliberate2")
    print( s )
    print( s.digest )
    assert s.digest == "972cca9b0dbb229ee21ce4667b7a30b742a16a502775fda18314d174"


def test_create_cn_spec():
    src_im_fp = Path(test_file).expanduser()
    img = Image.open(src_im_fp)
    s = StableSpec(uid="test",
                   prompt="photo of a garden fairy",
                   seed=1,
                   model_hash="deliberate2",
                   ctrlnet={'image': img}
                   )
    print( s )
    print( s.digest )
    assert s.digest == "e25c1096d3acfbcd0db6c35f3081b9f2936f1d47766e65f8712b9198"

@pytest.mark.skipif(not settings.stableforge.enabled, reason='stableforge disabled')
def test_get_api():
    api = WebUIApi( settings.stableforge.workers[0] )
    print( api )

@pytest.mark.skipif(not settings.stableforge.enabled, reason='stableforge disabled')
def test_basic_txt2img():

    api = WebUIApi( settings.stableforge.workers[0] )
    s = StableSpec(uid="test", prompt="a boat", model_hash="protogen58")
    img = api.txt2img(s)  # type: Image
    assert img is not None
    print( img.size )
    assert img.size == (320, 320)
    # img.show()

@pytest.mark.skipif(not settings.stableforge.enabled, reason='stableforge disabled')
def test_hi_res_txt2img():
    api = WebUIApi( settings.stableforge.workers[0] )
    s = StableSpec(uid="test",
                   prompt="a boat",
                   model_hash="deliberate2",
                   hires_fix={'scale': 2.0}
                   )
    img = api.txt2img(s)  # type: Image
    assert img is not None
    img.show()
    # print( img.size )
    assert img.size == (640, 640)


@pytest.mark.skipif(not settings.stableforge.enabled, reason='stableforge disabled')
# @pytest.mark.xfail(raises=KeyError)
def test_ctrlnet_txt2img():
    api = WebUIApi( settings.stableforge.workers[0] )
    src_im_fp = Path(test_file).expanduser()
    img = Image.open(src_im_fp)
    s = StableSpec(uid="test",
                   prompt="photo of a garden fairy",
                   model_hash="deliberate2",
                   ctrlnet={'image': img,
                            'processor': 'depth',
                            'model_name': 'depth'},
                   dims=img.size
                   )
    print( s )
    # img = api.txt2img(s)  # type: Image
    # assert img is not None
    # img.show()
    # print( img.size )
    # assert img.size == (640, 640)

    s = StableSpec(uid="test",
                   prompt="photo of a garden fairy",
                   model_hash="deliberate2",
                   ctrlnet={'image': src_im_fp,
                            'processor': 'depth',
                            'model_name': 'depth'},
                   dims=img.size
                   )

    img = api.txt2img(s)  # type: Image
    assert img is not None
    img.show()


@pytest.mark.skip()
def test_xmp():
    fp = Path(test_file).expanduser()
    spec = StableSpec(uid="abc-123", prompt="test prompt", neg_prompt="test neg",
                      meta={'actors': ['aria the bard', 'katya'], "nsfw": True})

    # write_xmp( fp, spec )
    # read_xmp( fp )

    write_xmp_sidecar(fp, spec)

    # fn = "~/resources/abc.xmp"
    # fn = Path(fn).expanduser()
    # with open(fn, 'rb') as f:
    #     metadata = pyexiv2.ImageData( f.read())
    # print( metadata.read_xmp() )
    # metadata.modify_xmp({'Xmp.dc.creator': ['tdev123']})

@pytest.mark.skipif(not settings.stableforge.enabled, reason='stableforge disabled')
def test_stableforge():
    forge = StableForge('default', apis=settings.stableforge.workers)
    s = StableSpec(uid="test", prompt="a boat", model_hash="deliberate2")
    img = forge.spec2img(s)  # type: Image
    assert img is not None
    print( img.size )
    assert img.size == (320, 320)
    # img.show()


# language=YAML
shotlist_ = """
shot_types:
  boat:
    prompt: '{{ role.actor }} standing on a boat {{ loc.text }}'
    hi_res:
      scale: 2.0

shot_vars:
  roles:
    person1:
      actor: abc
    person2:
      actor: def
    person3:
      actor: ghi

  locs:
    ocean:
      text: in the stormy ocean

shots:
  boat-person1-ocean:
    template: boat
    role: person1
    loc: ocean

  # this will create 2 shot specs
  _:
    uid: boat-{{ role.uid }}-ocean
    template: boat
    role: [ person2, person3 ]
    loc: ocean
"""

def test_shotlist():
    data = yaml.safe_load(shotlist_)

    shotlist = StableForge.load_shotlist( data )
    print( shotlist )
    assert len(shotlist) == 3
