## Why

Write methods (`_put`, `_post`) accept `dict[str, Any]` for request bodies, forcing users who read typed Pydantic models via `model=` to manually call `.model_dump()` before writing back. This breaks the round-trip ergonomics: the read path is clean (`model=User` returns a `User`), but the write path requires the user to know about serialization details.

## What Changes

- Add a `Dumpable` runtime-checkable `Protocol` that matches any object with a `dump(mode: str) -> dict[str, Any]` method (structurally satisfied by alma_models' base class).
- Add a `Body` type alias (`dict[str, Any] | Dumpable`) for use in write method signatures.
- Auto-convert `Dumpable` objects passed as `json=` kwargs in `AlmaClient.execute()`, calling `.dump(mode="json")` before the retry loop.
- Update all public namespace write method signatures from `dict[str, Any]` to `Body`.

## Capabilities

### New Capabilities
- `dumpable-body`: Protocol-based auto-serialization of model objects in write methods

### Modified Capabilities

## Impact

- `_utils.py`: New `Dumpable` protocol and `Body` type alias
- `_client.py`: 2-line conversion check in `execute()` before retry loop
- `_users.py`, `_bibs.py`, `_acq.py`, `_config.py`: Signature changes on write methods (`dict[str, Any]` -> `Body`)
- Fully backwards-compatible: existing code passing dicts is unaffected
- No new dependencies: uses `typing.Protocol` and `typing.runtime_checkable` from stdlib
- alma_models satisfies `Dumpable` structurally with no changes needed on that side
