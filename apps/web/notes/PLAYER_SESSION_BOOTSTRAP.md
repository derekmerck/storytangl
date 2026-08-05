# Player Session Bootstrap

**Status:** Current browser/session transport contract.

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
4. Recovery uses `POST /user/create?secret=...`: an existing codename restores
   its existing user; a new one creates a user. The operation supplies the
   intent, so identical bearer values are not treated as an error here.
5. Authenticated rotation uses `PUT /user/secret?secret=...`. It preserves the
   current UUID; a codename owned by another user conflicts rather than merging
   identities. Rotating to the current codename is a no-op.

The account surface displays and copies the browser-held recovery codename. It
does not fetch a plaintext secret from backend storage.

## Scope and follow-up

These codenames are memorable recovery capabilities, not passwords or a claim
of cryptographic account protection. Authentication/security policy, identity
providers, expiry, and permissions are explicitly outside this contract.

[Issue #352](https://github.com/derekmerck/storytangl/issues/352) owns the
remaining collision hardening, persistent-restart coverage, browser E2E,
`RemoteServiceManager` parity, and world-themed namebank follow-ups.
