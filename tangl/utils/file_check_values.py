import io

from pathlib import Path
from hashlib import sha224 as hash_func
from datetime import datetime

def compute_file_hash(arg: Path | io.IOBase ) -> bytes:

    if isinstance(arg, Path) and arg.is_file():
        with open(arg, 'br') as f:
            data = f.read()

    elif isinstance(arg, io.TextIOBase):
        data = arg.read()
        data = data.encode('utf-8')

    elif isinstance(arg, io.BytesIO):
        data = arg.read()

    h = hash_func(data)
    return h.digest()

def get_file_mtime( arg: Path | io.IOBase ):
    if isinstance(arg, io.FileIO):
        arg = arg.name

    return datetime.fromtimestamp(arg.stat().st_mtime)

