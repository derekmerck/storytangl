# WebTangl

Uses Vue 3 + TypeScript + Vite

## Config

Set these in `.env.local` or pass as build-args.

```shell
# Should def ask api for this
VITE_DEFAULT_API_URL=https://app.storytan.gl/api/v2
VITE_DEFAULT_WORLD=tangl_world
VITE_DEFAULT_USER_SECRET="<--webtangl-->"

# Default is client served off root
VITE_CLIENT_APP_PATH=/
VITE_CLIENT_APP_VERSION=2.7

VITE_DEBUG=true
# Only active with debug=true
VITE_MOCK_RESPONSES=true
VITE_SHOW_RESPONSES=true
```

## Type Support For `.vue` Imports in TS

TypeScript cannot handle type information for `.vue` imports by default, so we replace the `tsc` CLI with `vue-tsc` for type checking. In editors, we need [TypeScript Vue Plugin (Volar)](https://marketplace.visualstudio.com/items?itemName=Vue.vscode-typescript-vue-plugin) to make the TypeScript language service aware of `.vue` types.

If the standalone TypeScript plugin doesn't feel fast enough to you, Volar has also implemented a [Take Over Mode](https://github.com/johnsoncodehk/volar/discussions/471#discussioncomment-1361669) that is more performant. You can enable it by the following steps:

1. Disable the built-in TypeScript Extension
   1. Run `Extensions: Show Built-in Extensions` from VSCode's command palette
   2. Find `TypeScript and JavaScript Language Features`, right click and select `Disable (Workspace)`
2. Reload the VSCode window by running `Developer: Reload Window` from the command palette.

## Exporting the typescript spec from the backend

Use the [pydantic-to-typescript](https://github.com/phillipdupuis/pydantic-to-typescript) python package.

`pydantic2ts --module tangl.service.remote_api --tangl_types.ts`

`pydantic-to-typescript` requires a minor fix to recurse into GenericAliases
like `<list[MyModel]>`

  - script:66:
    > if not inspect.isclass(obj) or type(obj) is types.GenericAlias:
  - script:87:
    > for _, model in inspect.getmembers(module,
    >          lambda x: type(x) is types.GenericAlias and
    >                    is_concrete_pydantic_model(x.__args__[-1])):
    >     models.append(model.__args__[-1])