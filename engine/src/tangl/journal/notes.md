> Status: Historical / not authoritative
> Authority: Current fragment contracts live in `tangl.journal.fragments` and `docs/src/design/story/JOURNAL_COMPOSE_CONTRACT.md`.
> Current contract: use `tangl.journal.fragments` for fragment and hint models, `docs/src/design/story/JOURNAL_COMPOSE_CONTRACT.md` for post-merge composition, and `tangl.service.response` for service-native runtime payloads.

This should be called journal repr or stream repr or something fr = fabula/input/script, sr = syuzhet/output/fragment stream?

journal fragment stream:

- base_fragment
  - content fragment
    - narrative fragment/hints
      - dialog uses group fragment
    - media fragment/hints
  - control fragment
    - group fragment
    - ux modify fragment
    - ux signal fragment
  - info fragment (hinted kv)

response:  (service level)

- content response
  - slice of post-processed fragments
  - resolve media RITs to client format
  - convert native md text to client format

- info response
  - runtime info (cur task)
  - story info (ledger/graph state, may be customized)
  - world info
  - user info
  - system info
