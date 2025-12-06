# Changelog

## [Unreleased]

### Changed
- **BREAKING**: `Ledger.call_stack` now serializes with ledger JSON. Previously it was
  excluded, which meant REST save/resume during active calls dropped the stack. Old
  payloads missing `call_stack` still deserialize with an empty stack.

### Added
- `StackSnapshot` record type for event-sourced stack reconstruction.
- `Ledger.recover_stack_from_stream()` for time-travel/undo rebuilding the call stack.
- `Ledger.undo_to_step()` for rewinding ledger state using stream history.
- Automatic stack snapshots emitted after each step via the orchestrator.

### Fixed
- Call stacks now persist across REST save/resume flows.
- Time-travel/undo reconstructs a consistent graph and call stack state.
