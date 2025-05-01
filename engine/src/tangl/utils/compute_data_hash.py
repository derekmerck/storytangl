from pathlib import Path
import io
from hashlib import sha224 as hash_func

from tangl.type_hints import Hash   # bytes

def compute_data_hash(data: bytes | str | Path | io.IOBase) -> Hash:
    # centralizing this allows us to keep the hashing func and return type consistent

    if isinstance(data, Path):
        if data.is_file():
            with open(data, 'br') as f:
                data = f.read()
        else:
            raise ValueError(f"No such file {data}")

    elif isinstance(data, io.IOBase):
        data = data.read()  # If it's text io, we convert to bytes in final check

    if isinstance(data, str):
        data = data.encode('utf-8')

    return hash_func(data).digest()
