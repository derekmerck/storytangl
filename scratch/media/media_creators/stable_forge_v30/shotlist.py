"""
A `shotList` is a procedurally generated list of StableforgeSpec's.

This module provides two functions:

- `make_shotlist(templates, variable_maps, parameters, spec_class) -> list[StableforgeSpec]`
- `load_shotlist(yaml_file) -> list[StableforgeSpec]`

`make_shotlist` takes three dictionaries as input and a spec-class to generate.

- shot_types: a dictionary of default parameters for each named shot type.
- shot_vars: rules for how to map variable names in a set of parameters to template variables, ie, roles in shot parameters can be dereferenced to specific actors
- shot_configs: the actual configurations for the specific shots being generated

It returns a list of StableforgeSpec's of whatever subclass was given.

`load_shotlist` is a convenience function that loads a yaml file and passes the templates, variable_maps, and parameters fields to the `make_shotlist` function.

Use StableForge.render_specs() to render the list of specs.

Depends on the `rejinja2` module from tangl.
"""
from collections import ChainMap
from pathlib import Path
import logging
logger = logging.getLogger("tangl.media")

import jinja2
import yaml
import attr

from tangl.utils.dict_product import dict_product
from tangl.utils.rejinja import RecursiveTemplate
from .stable_spec import StableForgeSpec


def _expand_config_variants(shot_types: dict, shot_vars: dict, shot_config: dict) -> list[dict]:
    # use discrete names in var map, not like "abc" or it will find them in the uid

    shot_type = shot_config.get('shot_type')
    if not shot_type:
        for t in shot_types:
            if t in shot_config['uid']:
                shot_type = t
                break
    if not shot_type:
        shot_type = "narrative"
        # raise ValueError("Unable to deduce shot type")

    shot_type_template = shot_types[shot_type]
    config = ChainMap( shot_config, shot_type_template )

    config_variants = dict_product(config, ignore=["dims"])
    return config_variants


def _render_config(shot_vars: dict, config: dict) -> dict:

    env = jinja2.Environment(undefined=jinja2.StrictUndefined)

    # render the uid _before_ substitution so {{ role }} -> the role name, not the value
    t = env.from_string(config['uid'],
                        globals=config,
                        template_class=RecursiveTemplate)
    rendered = t.render()
    config['uid'] = rendered

    # dereference this config, role = abc -> {{ role.foo }} -> {{ abc.foo }}
    for var_name, var_dict in shot_vars.items():     # for k, v in { role: {'abc': ...}, locs: ... }
        config_val = config.get(var_name)            # config has a field 'role' with value 'abc'
        if config_val and config_val in var_dict:
            config[var_name] = var_dict[config_val]  # substitute with my v['abc']
        elif config_val:
            raise KeyError(f"No key {config_val} in {var_name} ({list(var_dict.keys())})")
        else:
            for k, v in var_dict.items():            # check for any of my keys in uid
                if k in config['uid']:               # abc-does-this
                    config[var_name] = v
                    break

    for key in ['prompt', 'neg_prompt']:
        if key not in config:
            continue
        t = env.from_string(config[key],
                            globals=config,
                            template_class=RecursiveTemplate)
        rendered = t.render()
        logger.debug( f"{key}: {rendered}" )
        config[key] = rendered

    return config


def _config_to_spec(config: dict, spec_class: type[StableForgeSpec] = StableForgeSpec) -> StableForgeSpec:

    kwargs = {}
    for field in attr.fields(StableForgeSpec):
        if field.name in config:
            kwargs[field.name] = config[field.name]
    spec = spec_class(**kwargs)
    return spec


def make_shotlist(shot_types, shot_vars, shot_configs,
                  spec_class: type[StableForgeSpec] = StableForgeSpec) -> list[StableForgeSpec]:
    """
    There are 3 parts to a shotlist:

    - shot-types: templates
    - shot-vars: dereferencing vars
    - shot-configs: parameters to be expanded into specs

    Configs with list-valued-keys will be expanded to generate multiple
    shots covering the product of all possible parameters

    ```yaml
    shot_types:
      boat:
        prompt: {{ role.actor }} standing on a boat {{ loc.text }}
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

    shot_configs:
      boat-person1-ocean:
        template: boat
        role: person1
        loc: ocean

      # this will create 2 shot specs and update the uid with the role selected
      _:
        uid: boat-{{ role }}-ocean
        template: boat
        role: [ person2, person3 ]
        loc: ocean
    ```

    shot_types can be processed by a forge-hook "_process_shot_types"
    shot_specs can be processed by a forge-hook "_process_shot_specs"

    """
    all_variants = []
    for uid, shot_config in shot_configs.items():
        if 'uid' not in shot_config:
            shot_config['uid'] = uid
        variants = _expand_config_variants(shot_types, shot_vars, shot_config)
        all_variants += variants

    all_specs = []
    for variant in all_variants:
        rendered_variant = _render_config(shot_vars, variant)
        spec = _config_to_spec(rendered_variant, spec_class)
        all_specs.append(spec)

    return all_specs


def load_shotlist(fp: Path | str):
    with open(fp) as f:
        data = yaml.safe_load(f)
    return make_shotlist(data['shot_types'], data['shot_vars'], data['shot_configs'])
