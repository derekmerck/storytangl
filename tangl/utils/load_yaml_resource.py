import io
from importlib import resources
from pathlib import Path

import yaml

from tangl.utils.file_check_values import compute_file_hash, get_file_mtime
from tangl.utils.shelved2 import shelved, clear_shelf

SHELF_FN = "yaml_loader"

@shelved(fn=SHELF_FN)
def cached_yaml_loader(path: Path, check_value=None):
    # check_value is used to invalidate stale entries
    with open(path) as f:
        return yaml.safe_load(f)

def load_yaml_resource(resource_module, yaml_fn, clear_cache=False):
    if clear_cache:
        clear_shelf(SHELF_FN)
    resources_dir = resources.files(resource_module)
    yaml_fp = resources_dir / yaml_fn
    check_value = (compute_file_hash(yaml_fp), get_file_mtime(yaml_fp))
    return cached_yaml_loader(yaml_fp, check_value=check_value)

@shelved(fn=SHELF_FN)
def cached_yaml_text_loader(text: str):
    # check_value is used to invalidate stale entries
    return yaml.safe_load(text)

def load_yaml_text(text: str, clear_cache=False):
    if clear_cache:
        clear_shelf(SHELF_FN)
    return cached_yaml_text_loader(text)
