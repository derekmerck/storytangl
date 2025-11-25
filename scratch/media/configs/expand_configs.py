"""
Expand Configs

Expand a configuration dict into many variants by recursively rendering strings
given a product of all possible variable configurations.

- expand_yaml( data ) -> list( dict )
- expand_configs( templates, vars, configs ) -> list( dict )
- create_config( template, vars ) -> list( dict )

Depends on `tangl.utils.rejinja` and `tangl.utils.dict_prod`

Specifically used in generating media 'shot lists' for various conditions
"""

from pathlib import Path
from pprint import pprint
import logging
from copy import copy
import math

import jinja2
import yaml

from tangl.utils.dict_product import dict_product
from tangl.utils.rejinja import RecursiveTemplate

logger = logging.getLogger("tangl.media")

def render_str(s: str, vars: dict):
    try:
        t = jinja2.Environment().from_string(s, template_class=RecursiveTemplate, globals=vars)
        res = t.render()
        return res
    except TypeError:
        logging.error(f"Failed to compile val: {s}")

from collections import ChainMap

def create_config(template: dict, *config_vars: dict) -> dict:
    config_vars = { **ChainMap( *reversed(config_vars) ) }
    res = {}
    for k, v in template.items():
        if isinstance(v, str):
            res[k] = render_str(v, config_vars)
        else:
            res[k] = v
    return res

def expand_config(templates, config_vars, config) -> list[dict]:
    template = copy( templates.get( config.pop( 'template' ) ) )
    template['uid'] = config.pop('uid')
    variant_configs = dict_product(config)
    # double check that the dict prod worked as expended
    assert( math.prod( [ len(v) for v in config.values() if isinstance(v, list) ] ) ) == len( variant_configs)
    logger.debug(f'generating {len(variant_configs)} new configs')
    # pprint( variant_configs )
    res = []
    for vc in variant_configs:
        # vars_ = vars | vc
        new_config = create_config( template, config_vars, vc )
        # pprint( new_config )
        res.append(new_config)
    return res

def expand_configs(templates: dict, vars: dict, configs: dict) -> list[dict]:
    res = []
    for uid, config in configs.items():
        config['uid'] = config.get('uid', uid)
        res.extend( expand_config(templates, vars, config) )
    return res

def expand_yaml_configs(fp_or_str: Path | str) -> list[dict]:
    """
    There must be exactly 3 keys in a spec config yaml file:

    - templates
    - vars
    - configs

    Configs with list-valued-keys will be expanded to generate multiple
    specs covering the product of all possible parameters
    """
    try:
        fp = Path(fp_or_str).expanduser()
        with open(fp) as f:
            data = yaml.safe_load(f)
    except (FileNotFoundError, ValueError, OSError):
        data = yaml.safe_load(fp_or_str)

    return expand_configs(**data)
