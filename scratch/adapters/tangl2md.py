"""
Renders out an entirely materialized story as a cyoa-style e-book.

Requires [pypandoc](https://github.com/NicklasTegner/pypandoc), [pandoc-secnos](https://github.com/tomduck/pandoc-xnos)
"""
import os
from pathlib import Path

import pypandoc
import jinja2

from tangl.story.fabula import World
from tangl.story.story_graph import Story
from tangl.utils.deep_md import deep_md
from tangl.lang.helpers import oxford_join

IMAGE_FORMAT = "png"

# Set the world dir to render a single world
world_id = "sample_world"

# This template gives scenes _in ordered hierarchy_.  May want to shuffle all
# blocks and use flat numbering for all worlds together just for fun...

# language=jinja2
templ_ = """
---
title: {{ wo.label }}
author: {{ author_str(wo) }}
...
{% for sc in scenes %}
{{ sc.label() }}
==========================

{% for bl in sc.blocks.values() %}

{{ "{{#sec:{0}}}".format(bl.pid) }}
--------------------------

{% for ref in bl.redirects %}
- First read (@sec:{{ ref.follow().pid }})
{% endfor %}

{{ bl.desc() }}

{% for im in bl.images() or [] %}
![](_images/{{im | im_fn(bl.path, fmt=fmt) }})
{% endfor %}

{% for ac in bl.actions %}
- {{ ac.label() }} (@sec:{{ ac.follow().pid }})
{% endfor %}

{% for ref in bl.continues %}
- Continue (@sec:{{ ref.follow().pid }})
{% endfor %}

{% endfor %}

{% endfor %}
"""

def im_fn( im: str, new_uid: str, fmt="svg" ) -> str:
    # todo: this maps ref avatars to a block role so they won't be repeatedly rendered,
    #       but it won't work with created actor avatars
    if im.startswith("avatar") and new_uid:
        im = f"avatar/{new_uid}"
    fn = im.replace("/", "-") + "." + fmt
    return fn

def author_str(wo: World) -> str:
    res = oxford_join( [ a['name'] for a in wo.info['authors'] ] )
    return res

def dump_images( ctx: Story, fmt="svg" ):

    scenes = ctx.get_scenes()

    os.makedirs( "_images", exist_ok=True )
    for sc in scenes:
        for bl in sc.blocks.values():
            # if "skip_graph" in bl.locals:
            #     continue
            r = bl.render()
            for im in r.get('images', []):
                if not im:
                    print( f"Missing images in {bl.path}")
                    continue
                fn = im_fn( im, bl.path, fmt=fmt )
                if os.path.isfile( os.path.join( "_images", fn ) ):
                    continue
                print( f"rendering {fn} ")
                if im.startswith('avatar'):
                    uid = im.split("/")[1]
                    try:
                        data = ctx[uid].get_image( fmt=fmt )
                    except:
                        pass
                else:
                    data = wo.get_scene_art( im, fmt=fmt )
                if fmt == "svg":
                    open_flags = "w"
                else:
                    open_flags = "wb"
                with open( os.path.join( "_images", fn ), open_flags ) as f:
                    f.write( data )


def render_to_md( wo: World ) -> str:
    """
    Generate markdown version of story
    """

    ctx = wo.new_context() # type: Context
    scenes = ctx.get_scenes()

    # sort entry to front
    entry = ctx[wo.entry.split("/")[0]]
    scenes.remove( entry )
    scenes.insert( 0, entry )

    dump_images( ctx, fmt=IMAGE_FORMAT )
    e = jinja2.Environment()
    e.filters['im_fn'] = im_fn
    e.globals['author_str'] = author_str
    # e.filters['md'] = deep_md
    templ = e.from_string( templ_ )
    res = templ.render( scenes=scenes, wo=wo, fmt=IMAGE_FORMAT )
    return res


def render_to_epub( wo: World, epub_cover: str = None):
    """
    Generate markdown version of story and convert to epub format using Pandoc
    """

    res = render_to_md( wo )
    print( res )

    extra_args = ['--number-sections']

    if epub_cover or "epub_cover" in wo.info:
        epub_cover = Path( wo.info.get( 'epub_cover', epub_cover ) )
        epub_cover_file = Path("_images") / epub_cover.parts[-1]
        extra_args.append( f'--epub-cover-image={epub_cover_file}' )

    # if not os.path.isfile(os.path.join("_images", epub_cover)):
    #     cover_data = wo.get_scene_art( epub_cover )
    #     if False:  # todo: re-enable cover_data:
    #         epub_cover = epub_cover.replace( "media", "_images" )
    #         with open( epub_cover, 'wb' ) as f:
    #             f.write( cover_data )

    output = pypandoc.convert_text(res, 'epub', 'markdown+raw_html',
                                   extra_args=extra_args,
                                   outputfile=wo.label + ".epub",
                                   filters=['pandoc-secnos'])


if __name__ == "__main__":

    wo = World.load( wo_ )
    render_to_epub( wo )
