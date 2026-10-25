# Reference browser smoke

From the repository, install the Poetry development dependencies. From `apps/web`:

```sh
yarn install --frozen-lockfile
yarn playwright install chromium
yarn type-check
yarn test --run
yarn build:e2e
yarn test:e2e
```

On Linux, use `yarn playwright install --with-deps chromium` for browser system
dependencies. Playwright and its matching Chromium revision are pinned in the
lockfile. On machines with a slow/unwritable matplotlib cache, set
`MPLCONFIGDIR=/private/tmp/issue571-mpl` and `MPLBACKEND=Agg` for the test command.

Playwright owns readiness and cleanup for one server on port 4173, and refuses
to reuse an existing server. The server copies only the checked-out `reference`
bundle into a temporary world root, isolates cache/user/story paths, and serves
Vite's built dist through the real top-level `tangl.rest.app`. Persistence is
native in-memory and lasts for this server process. The browser uses one worker,
a fresh context, no stored secret, blocked service workers, and no MSW or route
fulfilment. Required reference SVGs must be present and decodable.

The witness checks fresh-player bootstrap, actual catalog selection, one
creation, exact offered edge IDs for two moves, status, and same-server reload
with the same player/ledger and only the current choice occurrences enabled.
It checks DOM and network outcomes and fails on browser errors, failed requests,
or unsuccessful API/media responses. This does not prove Service-restart or
cross-browser JSON recovery, audio playback, or staging/presentation parity.

Failure artifacts are `test-results/` (screenshot, trace, request/response/error
attachment), `playwright-report/`, and `e2e-artifacts/server.log`. Open a trace
with `yarn playwright show-trace <trace.zip>`. CI uploads these on failure.
The always-reported Web Client Gate requires Chromium and component checks on
relevant web/server/engine/world/config/lock/workflow changes. Docs-only changes
skip the browser installation and explicitly pass the gate's skip condition.
