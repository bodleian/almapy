# dumpable-body Specification

## Purpose

Allow almapy write methods to accept request bodies either as plain `dict[str, Any]` or as any object that structurally satisfies a `Dumpable` Protocol (e.g. alma_models Pydantic models), converting Dumpable objects to JSON-serialisable dicts automatically before the request is sent.

## Requirements

### Requirement: Dumpable Protocol definition
The library SHALL define a `@runtime_checkable` Protocol named `Dumpable` in `_utils.py` with a single method: `dump(self, mode: str = ...) -> dict[str, Any]`. The library SHALL also define a type alias `Body = dict[str, Any] | Dumpable`.

#### Scenario: alma_models base class satisfies Dumpable structurally
- **WHEN** an alma_models model instance is checked with `isinstance(obj, Dumpable)`
- **THEN** the check SHALL return `True` without alma_models importing or inheriting from almapy

#### Scenario: Plain dict does not satisfy Dumpable
- **WHEN** a `dict[str, Any]` is checked with `isinstance(obj, Dumpable)`
- **THEN** the check SHALL return `False`

### Requirement: Auto-conversion of Dumpable objects in execute
`AlmaClient.execute()` SHALL detect when `kwargs["json"]` is a `Dumpable` instance and replace it with the result of `.dump(mode="json")` before entering the retry loop.

#### Scenario: Pydantic model passed as json kwarg
- **WHEN** a `Dumpable` object is passed as `json=` to any write method
- **THEN** `execute()` SHALL call `.dump(mode="json")` on it and pass the resulting dict to the HTTP client

#### Scenario: Dict passed as json kwarg (backwards compatibility)
- **WHEN** a `dict[str, Any]` is passed as `json=` to any write method
- **THEN** `execute()` SHALL pass it through unchanged to the HTTP client

#### Scenario: Conversion happens once before retry loop
- **WHEN** a `Dumpable` object triggers retries due to transient errors
- **THEN** `.dump(mode="json")` SHALL be called exactly once, before the first attempt

### Requirement: Write method signatures accept Body type
All public namespace methods that accept a request body as `dict[str, Any]` SHALL update their type annotation to `Body`. The existing two-overload pattern (one with `model: type[_ModelT]`, one with `model: None`) SHALL be preserved — only the body parameter type changes.

#### Scenario: IDE shows model support in autocomplete
- **WHEN** a user inspects the type of a write method's body parameter
- **THEN** the type SHALL be `Body` (i.e. `dict[str, Any] | Dumpable`)

#### Scenario: Existing dict-based calls remain valid
- **WHEN** existing code passes `dict[str, Any]` to a write method
- **THEN** the call SHALL type-check and execute identically to before

### Requirement: Explicit model= required for typed responses
Write methods SHALL NOT auto-infer the return type from the body type. The user MUST pass `model=` explicitly to receive a typed response, consistent with read methods.

#### Scenario: Dumpable body without model= returns Box
- **WHEN** a `Dumpable` object is passed as the body without `model=`
- **THEN** the method SHALL return `RESP_TYPE` (Box), not the body's type

#### Scenario: Dumpable body with model= returns typed model
- **WHEN** a `Dumpable` object is passed as the body with `model=User`
- **THEN** the method SHALL return a `User` instance
</content>
</invoke>
