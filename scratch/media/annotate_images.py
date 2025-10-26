"""
Read png image files created by Auto1111 stable diffusion, display their
annotations as a StableforgeSpec, and optionally convert annotations to xmp
for use with other applications.

Note that Lightroom Classic does _not_ support sidecar annotations for png.

Requires pyexiv2 to generate xmp data.
"""

import logging
logger = logging.getLogger("tangl.media")

import click
from pathlib import Path
from PIL import Image
from pprint import pprint

from tangl.media.stableforge.auto1111_spec import Auto1111Spec
from tangl.media.stableforge.xmp_handler import XmpDataModel

@click.command()
@click.option('-d', '--display-info', is_flag=True, default=False, help='Display info.')
@click.option('-g', '--generate-xmp', is_flag=True, default=False, help='Generate a XMP dict.')
@click.option('-i', '--inline-xmp', is_flag=True, default=False, help='Generate and annotate with inline XMP.')
@click.option('-s', '--sidecar-xmp', is_flag=True, default=False, help='Generate and annotate with XMP side-vehicle.')
@click.argument('files', nargs=-1, type=click.Path(exists=True))
def annotate_images(generate_xmp, inline_xmp, sidecar_xmp, display_info, files):
    for fp in files:
        annotate_image(fp, generate_xmp, inline_xmp, sidecar_xmp, display_info)

def annotate_image(fp: str | Path,
                   generate_xmp: bool = True,
                   inline_xmp: bool = False,
                   sidecar_xmp: bool = False,
                   display_info: bool = False) -> None:

    fp = Path(fp)
    im = Image.open(fp)
    try:
        info = im.info['parameters']
        if display_info:
            logger.info("-------INFO-------")
            logger.info(info)
    except KeyError:
        logger.error("-------FAILED-------")
        logger.error(im.info)
        return
        # raise
    spec = Auto1111Spec.from_info(info, str(fp))
    logger.debug("-------SPEC-------")
    logger.debug(spec)
    if generate_xmp or inline_xmp or sidecar_xmp:
        logger.debug("-------XMP-------")
        data = spec.as_xmp()
        pprint(data)

        if inline_xmp:
            logger.debug("--> Added inline xmp")
            XmpDataModel.write_xmp(fp, spec)
        elif sidecar_xmp:
            logger.debug("--> Added sidecar xmp")
            XmpDataModel.write_xmp_sidecar(fp, spec)


if __name__ == '__main__':
    annotate_images()
