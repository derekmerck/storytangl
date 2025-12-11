
from __future__ import annotations
import re
import sys
import importlib
import types
from pathlib import Path
from typing import *

import yaml

from tangl.import config
from tangl.svgforge.svg_factory import SvgFactory as SvgForge
from tangl.utils.glob2dict import glob2dict
from tangl.utils.bunch import Bunch, Spans


class WorldLoader:

    @classmethod
    def _load_cls_template_maps(cls, base_path: Path, templates_paths: dict[str, str]) -> dict:
        data = {}
        for k, v in templates_paths.items():
            data[k] = {}
            templs = glob2dict(base_path, v)
            for uid, templ in templs.items():
                data[k][uid] = templ
        return data

    @classmethod
    def load(cls, base_path: Union[Path, str] = None) -> "World":


        if isinstance( base_path, str ):
            base_path = Path( base_path )

        if not base_path.is_dir():
            base_path = config.worlds_path / base_path

        if not base_path.is_dir():
            raise FileNotFoundError

        with open( base_path / "world.yaml" ) as f:
            spec = yaml.safe_load( f )
            # spec includes entries for uid, label, desc, spans, icons;
            # templates_paths and backend_ui are popped and decomposed

        uid = spec['uid']
        label = spec.get('label', uid)
        entry = spec.get('entry', 'main_menu')
        info = spec.get('info')
        pwl = Path.resolve( base_path / spec.get('pwl', 'pwl.txt') )
        ui_config = spec.get( "ui_config", {} )
        ui_config['spans'] = Spans(ui_config.get('spans'))
        ui_config['icons'] = Bunch(ui_config.get('icons'))

        # if "spans" in ui_config:
        #     ui_config['spans'] = Spans( ui_config['spans'] )
        # if "icons" in ui_config:
        #     ui_config['icons'] = Bunch( ui_config['icons'])

        template_paths = spec.get( "templates_paths" )
        cls_template_maps = cls._load_cls_template_maps( base_path, template_paths )

        pkg_ = spec.get("pkg", "pkg")
        # pkg = cls._load_hooks( base_path, hooks_path )
        sys.path.append( str( base_path) )
        pkg = importlib.import_module( pkg_ )
        sys.modules[uid] = pkg

        scene_art_path = spec.get("scene_art", "scene_art.svg" )
        try:
            scene_art = SvgForge.from_file( base_path / scene_art_path, preserve_styles=True )
        except FileNotFoundError:
            scene_art = None
            print( f"No scene art found for {spec['uid']} at {base_path / scene_art_path}")

        params = {'uid': uid,
                  'base_path': base_path,
                  'label': label,
                  'info': info,
                  'cls_template_maps': cls_template_maps,
                  'scene_art': scene_art,
                  'entry': entry,
                  'ui_config': ui_config,
                  'pwl': pwl }

        from .world import World
        wo = World( **params )

        return wo

    @classmethod
    def load_all( cls ):

        base_path = config.worlds_path
        world_files = base_path.glob("**/world.yaml")
        for wf in world_files:
            wp = wf.parent
            cls.load(wp)
