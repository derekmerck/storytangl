# Player Session Bootstrap

**Status:** Current browser/session transport contract; JSON backend restart and
fresh-context recovery have a separate real-browser witness in `e2e/README.md`.

The web client provides one small persistence capability for a single-player
story session. It is not an authentication or account framework.

## Ownership

- On a first visit, `POST /user/create` without a secret makes the server choose
  an unused memorable codename with `get_code_name()`. The response carries the
  plaintext codename and its stable user UUID.
- The browser owns that plaintext recovery codename and persists it in
  `localStorage`. The backend stores only its derived hash and the stable user
  UUID.
- A derived API key is a transport detail. It is derived from the codename,
  bound to requests, and validated with `GET /user/info`; it is not a second
  identity or an independent sign-in state.

## Lifecycle

1. A normal first visit silently creates a player and persists the returned
   codename before mounting the story application.
2. A normal return silently derives and validates the stored codename before
   mounting the application.
3. Missing or invalid browser state exposes the recovery surface. The player
   may recover with a codename, start a new player, or explicitly switch.
4. The browser's Use Existing Secret action derives the key and validates it
   through `GET /user/info`. An unknown codename stays at the recovery gate;
   it must not silently create another player. Start New Player owns creation.
   Service still supports explicit `POST /user/create?secret=...` callers;
   that create operation is separate from browser recovery.
5. Authenticated rotation uses `PUT /user/secret?secret=...`. It preserves the
   current UUID; a codename owned by another user conflicts rather than merging
   identities. Rotating to the current codename is a no-op.

The account surface displays and copies the browser-held recovery codename. It
does not fetch a plaintext secret from backend storage.

## Scope and follow-up

These codenames are memorable recovery capabilities, not passwords or a claim
of cryptographic account protection. Authentication/security policy, identity
providers, expiry, and permissions are explicitly outside this contract.

Collision rerolling, persisted recovery, and `RemoteServiceManager` parity are
covered by the service contract. Real-browser E2E remains with
[Issue #73](https://github.com/derekmerck/storytangl/issues/73); world-themed
namebanks remain deferred.
