"""
==> This module is broken and obsolete; it is included for legacy reference only.
==> `pydantic2ts` does not work well with pydantic v2 syntax.  It is fixable, but
==> not relevant as the current response models are fairly well settled.

This script exports the TypeScript spec of the api response models from the backend.

May need to use this if adding a totally new type of journal entry format that needs to be tightly integrated with new client code.

Run this and move output to `<project dir>/client/src/types/tangl_typedefs.ts`

Requires the [pydantic-to-typescript](https://github.com/phillipdupuis/pydantic-to-typescript) python package and its dependency, the [json2ts][] node package.

`pydantic-to-typescript.cli.script` requires a few fixes to recurse into GenericAliases
like `<list[MyModel]>` and then to addend our typed arrays and dicts.

66:
`if not inspect.isclass(obj) or type(obj) is types.GenericAlias:`

87:
```
for _, model in inspect.getmembers(module,
         lambda x: type(x) is types.GenericAlias and
                   is_concrete_pydantic_model(x.__args__[-1])):
    models.append(model.__args__[-1])
```

155: `def generate_json_schema(models: List[Type[BaseModel]], **kwargs) -> str:`

173:
```
master_model = create_model(
    "_Master_",
    **{m.__name__: (m, ...) for m in models},
    **kwargs
)
```

197:
```
def generate_typescript_defs(
    module: str, output: str, exclude: Tuple[str] = (), json2ts_cmd: str = "json2ts",
    **kwargs
) -> None:
```
script 225: `schema = generate_json_schema(models, **kwargs)`
"""

import warnings
import subprocess

from pydantic2ts import generate_typescript_defs

from tangl.media.enums import MediaRole

warnings.warn(
    "This module is broken and obsolete; it is included for legacy reference only.",
    DeprecationWarning, stacklevel=2)

module = "tangl.service.remote_service_api"
outfile = "tangl_typedefs.ts"
extras = {
    'MediaRole': (MediaRole, ...)
}
array_types = ['JournalBlocks',
               'StoryStatusModel',
               'WorldSceneList',
               'WorldList']


def generate_ts_defs(module, outfile, array_types, **extras):
    warnings.warn("This method is broken and obsolete; it is included for legacy reference only.", DeprecationWarning, stacklevel=2)

    generate_typescript_defs(module, outfile, **extras)

    # Generates a (string | string)[] type, which is improper
    cmd = ["sed", "-i", "", r's/(string | string)\[\]/string[]/g', outfile]
    subprocess.call(cmd)

    for name_ in array_types:
        type_ = locals().get(name_)
        s = f"export type {name_} = {type_.__args__[-1].__name__}[];\n"
        print( s )
        with open(outfile, "a") as f:
            f.write(s)

if __name__ == "__main__":
    generate_ts_defs(module, outfile, array_types, **extras)