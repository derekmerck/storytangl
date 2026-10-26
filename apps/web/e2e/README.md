# Reference browser smoke

From the repository, install the Poetry development dependencies. From `apps/web`:

```sh
yarn install --frozen-lockfile
yarn playwright install chromium
yarn type-check
yarn test --run
yarn build:e2e
yarn test:e2e
yarn test:e2e:restart
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

The separate `test:e2e:restart` witness owns two real backend processes on the
same port and one temporary JSON store. It copies the reference bundle once,
creates a player/story through the UI, takes two choices, gracefully stops the
first backend, and starts the second over the existing files. Readiness checks
use only system info: no world compilation, world-info warm-up, or replacement
story. Reload must restore the same player, ledger, cursor, step and current
choice occurrence/edge IDs, with history once and decoded SVG media.

A completely fresh browser context first creates an unrelated player with no
story. It then uses Switch or Recover Player and the original recovery secret
through the existing UI, without storage/cookie/header injection. Invalid-secret
recovery must stay at the gate without creating an account. Successful recovery
must show the original history/frontier/media, take a third choice and survive
reload. Supplemental requests using the unrelated player's observed credentials
must neither read nor advance that story. Both processes stop and the temporary
store is removed, including on failure. Run the two browser commands serially.

This checks identity and current-story continuity, not timestamp fidelity.
The existing `UserInfo.created_dt` drift observed across JSON restoration is
explicitly deferred; this witness does not fix or guarantee that timestamp.
See [the restoration fix](https://github.com/derekmerck/StoryTangl/pull/620).

Failure artifacts are `test-results/` (screenshot, trace, request/response/error
attachment), `playwright-report/`, and `e2e-artifacts/server.log`. Open a trace
with `yarn playwright show-trace <trace.zip>`. CI uploads these on failure.
JSON failure logs are `e2e-artifacts/json-a.log` and `json-b.log`; traces,
screenshots, network observations and process/identity receipts are under
`test-results/json-restart/`. Both witnesses reuse the pinned browser install.
The always-reported Web Client Gate requires both Chromium witnesses and component checks on
relevant web/server/engine/world/config/lock/workflow changes. Docs-only changes
skip the browser installation and explicitly pass the gate's skip condition.
