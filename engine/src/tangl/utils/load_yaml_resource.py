import io
from importlib import resources
from pathlib import Path

import yaml

from tangl.utils.hashing import compute_data_hash
from tangl.utils.get_file_mtime import get_file_mtime
from tangl.utils.shelved2 import shelved, clear_shelf

SHELF_FN = "yaml_loader"

@shelved(fn=SHELF_FN)
def cached_yaml_loader(path: Path, check_value=None):
    # check_value is used to invalidate stale entries
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_yaml_path(yaml_fp: Path):
    """Parse an already-resolved YAML file through the shelf, keyed by content and mtime."""
    check_value = (compute_data_hash(yaml_fp), get_file_mtime(yaml_fp))
    return cached_yaml_loader(yaml_fp, check_value=check_value)

def load_yaml_resource(resource_module, yaml_fn, clear_cache=False):
    if clear_cache:
        clear_shelf(SHELF_FN)
    return load_yaml_path(resources.files(resource_module) / yaml_fn)

# @shelved(fn=SHELF_FN)
# def cached_yaml_text_loader(text: str):
#     # check_value is used to invalidate stale entries
#     return yaml.safe_load(text)
#
# def load_yaml_text(text: str, clear_cache=False):
#     if clear_cache:
#         clear_shelf(SHELF_FN)
#     return cached_yaml_text_loader(text)
