"""
Hash-dir

Read in all py and yaml files, and compute the hash.

This can be used to pickle-cache world files or other data
sources, and only reread them when they are updated.
"""

from typing import *
from pathlib import Path
import hashlib
import base64


def hash_dir(base_path, exts: List = ('py', 'yaml'), chars = 12) -> str:
    # get the 'magic number' for the content
    if not isinstance(base_path, Path):
        base_path = Path( base_path )
    files = []
    for ext in exts:
        files.extend(base_path.rglob(f'*.{ext}'))
    h = hashlib.sha224()
    for file in files:
        with open(file, "br") as f:
            data = f.read()
            h.update(data)
    encoded = base64.b64encode(h.digest(), b"Aa")
    s = encoded.decode("utf8")
    return s[0:chars]
