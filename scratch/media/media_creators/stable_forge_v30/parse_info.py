from pathlib import Path
from pprint import pformat
import re
import logging

import yaml

logger = logging.getLogger(__name__)

def _info_to_yaml(info: str) -> str:
    """
    converts an auto1111 info into a yaml str.

    input data looks like this:

    data = \
        'pretty young woman katya, dark lips, lavender eyes, long legs, ' \
        'ponytail hair, (((classical japanese ink brush and woodblock ' \
        'art scroll)))\n' \
        'Steps: 20, Sampler: Euler a, CFG scale: 7, Seed: 2286316612, ' \
        'Size: 512x512'
    """
    # get rid of last line if necessary
    info = re.sub('\nUsed embeddings: .*', '', info)

    if not info.lower().startswith("negative"):
        # sometimes there is no prompt
        prompt = "prompt: " + "\n".join( info.splitlines()[:-1] ) + "\n"
    else:
        prompt = "\n".join( info.splitlines()[:-1] ) + "\n"

    prompt = re.sub( r"'", "", prompt)
    prompt = re.sub( r"([\w _]+:.*)", r"\n\1", prompt)  # add \n before keys
    prompt = re.sub( r"\n([\[\w(]+)", r"\1", prompt) # get rid of single newlines
    prompt = re.sub( r": +([\[(].*)\n", r": '\1'\n", prompt)
    prompt = re.sub( r" {2,}", r" ", prompt)
    prompt = re.sub( r"\(([\w ]+): ([\d.]+)\)", r"(\1:\2)", prompt)

    params = info.splitlines()[-1]
    params = re.sub(", ", "\n", params)
    data_ = prompt + params
    # logger.debug( data_ )
    return data_


def _load_yaml(data_: str) -> dict:
    """
    Load the yaml data into a dict and format it
    """
    try:
        res = yaml.safe_load(data_)
    except:
        logger.error("Unable to load yaml")
        logger.error( data_ )
        raise
    res = { k.lower(): v for k, v in res.items() }
    res = { k.replace(" ", "_"): v for k, v in res.items() }
    res['width'], res['height'] = res['size'].split('x')
    del res['size']
    return res

def parse_info(info: str) -> dict:
    """
    Convert an auto1111 info string into a stableforge spec
    """
    data_ = _info_to_yaml(info)
    data = _load_yaml(data_)
    return data
