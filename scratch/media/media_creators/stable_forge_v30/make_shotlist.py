from pprint import pprint
import logging

import yaml

from tangl.media import MediaReference as MediaRef
from tangl.media.has_media import HasMedia
from tangl.media.illustrated.stableforge import StableForge, Auto1111Spec
from tangl.world import World

logging.getLogger("tangl.rejinja").setLevel(logging.WARNING)
logging.getLogger("tangl.media.sf_spec").setLevel(logging.WARNING)

SPEC_TYPE = Auto1111Spec

def get_all_specs():
    """
    dict of all media refs with spec of SPEC_TYPE
    """
    res = {}
    for world_id in ['w1', 'w2', 'w3']:
        world = World[world_id]
        dummy = world.create_story(user=None)

        media_refs = dummy.find_nodes(types=(MediaRef,), filt=lambda x: isinstance(x.spec, Auto1111Spec))  # type: list[MediaRef]

        for mr in media_refs:
            spec = mr.spec.realize(ref=mr.parent)  # type: Auto1111Spec
            key = "/".join( [ world.label, mr.path ] )
            res[ key ] = {
                'role': str(mr.media_role),
                'prompt': spec.prompt,
                'n_prompt': spec.n_prompt
            }

    y = yaml.dump( res, sort_keys=False )
    print("---")
    print(f"# {SPEC_TYPE} SHOT LIST")
    print( y )

    return res

def get_shot(key: str, world_id = "ac1"):
    """
    Generate image corresponding to the ref at key, or at ref.media matching SHOT_TYPE
    """
    world = World[world_id]
    dummy = world.create_story(user=None)
    inst = dummy.find( key )
    if isinstance(inst, MediaRef):
        m_ref = inst
    elif isinstance(inst, HasMedia):
        m_ref = [ x for x in inst.media if isinstance(x.spec, SPEC_TYPE) ][0]
    else:
        raise KeyError( f"No valid node for {key}" )

    spec = m_ref.get_spec()

    api = StableForge.get_auto1111_api()
    im = api.generate_image(spec)

    im.show()


if __name__ == "__main__":
    # get_all_specs()
    get_shot("katya")
