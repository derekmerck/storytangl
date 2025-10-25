from __future__ import annotations
import logging
import math

import jinja2
from pydantic import BaseModel, Field, ValidationInfo, field_validator

from tangl.entity import SingletonEntity
from tangl.type_hints import Primitive, UniqueLabel
from tangl.utils.rejinja import DereferencingTemplate  # requires "python-box"
from tangl.utils.dict_product import dict_product

logger = logging.getLogger("tangl.promptforge")

class ConfigManager(BaseModel):
    """
    Recursively render text strings from complex nested and inter-linked configurations
    """
    config_templates: dict[str, ConfigTemplate]       # jinja template strings by key
    global_vars: dict = Field(default_factory=dict)   # global vars across all configs
    configs: dict[UniqueLabel, Config]                # individual config patterns

    @field_validator("configs", mode='before')
    @classmethod
    def _preprocess_configs(cls, data: dict, info: ValidationInfo):
        for k, v in data.items():
            v: dict
            # Since configs are singletons, each pattern needs a unique label that can be expanded
            v.setdefault('label', k)
            for t in info.data['config_templates'].keys():
                # Look for a template key in the label to set the template key
                if t in k:
                    # print(f"found template key {t}")
                    v.setdefault('template', t)
            # otherwise, default is "character"
            v.setdefault('template', "character")
            # make sure that there is a merge_keys value available to update
            v.setdefault('merge_keys', dict())
            for g in info.data['global_vars'].keys():
                # look for any global vars in the label to add to merge keys
                if g in k:
                    # print(f'found global {g}')
                    # we want the key-to-merge to be in _first_ so the other keys can depend on its content
                    v['merge_keys'] = {g: None, **v['merge_keys']}

        return data

    def get_j2_env(self) -> jinja2.Environment:
        env = jinja2.Environment()
        env.globals = self.global_vars
        env.template_class = DereferencingTemplate
        return env

    def get_j2_templ(self, key: str) -> jinja2.Template:
        config_template = self.config_templates[key]
        return self.get_j2_env().from_string(
            config_template.text,
            globals=config_template.default_vars)

    def render_config(self, config: Config | UniqueLabel):
        if isinstance(config, UniqueLabel):
            config = self.configs[config]
        templ = self.get_j2_templ(config.template_key)
        return templ.render(
            merge_keys=config.merge_keys,
            **config.local_vars)

    def expand_pattern(self, config: Config | UniqueLabel) -> list[Config]:
        if isinstance(config, UniqueLabel):
            config = self.configs[config]
        variant_local_vars = dict_product(config.local_vars)
        # double check that the dict prod worked as expended
        assert (math.prod([len(v) for v in config.local_vars.values() if isinstance(v, list)])) == len(variant_local_vars)
        logger.debug(f'generating {len(variant_local_vars)} new configs')
        # pprint( variant_configs )
        res = []
        for n, vc in enumerate(variant_local_vars):
            # vars_ = vars | vc
            new_config = Config(label=f"prompt-{n}",
                                template = config.template_key,
                                merge_keys = config.merge_keys,
                                local_vars = vc)
            # pprint( new_config )
            res.append(new_config)
        return res

    def update(self, data: dict):
        update_model = self.__class__(**data)
        self.config_templates.update( update_model.config_templates )
        self.global_vars.update( update_model.global_vars )
        self.global_vars.update( update_model.configs )

class ConfigTemplate(BaseModel):
    text: str
    default_vars: dict

    # @pydantic.model_validator(mode='after')
    # def _check_default_vars_complete(self):
    #     # todo: find all jinja expressions, make sure the names are in self.default_vars
    #     return self

class Config(SingletonEntity):
    template_key: str = Field(..., alias="template")
    merge_keys: dict[str, str | None | list] = Field(default_factory=dict)
    local_vars: dict[str, Primitive | dict | list] = Field(default_factory=dict)
