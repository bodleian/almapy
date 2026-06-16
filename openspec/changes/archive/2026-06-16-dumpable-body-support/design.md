## Context

almapy write methods (`_put`, `_post`) accept `dict[str, Any]` for request bodies. The companion library alma_models provides Pydantic models with a `.dump(mode="json")` method that handles alias mapping and JSON-safe serialization. Users who read via `model=` get typed objects back, but must manually call `.model_dump()` or `.dump()` to write them back. This breaks round-trip ergonomics.

## Goals / Non-Goals

**Goals:**
- Accept alma_models (or any object with a compatible `dump()`) directly in write methods
- Auto-convert at the `execute()` layer so all write paths benefit
- Maintain full backwards compatibility with dict-based usage
- Provide IDE-visible type information via a `Body` type alias

**Non-Goals:**
- Supporting arbitrary serialization protocols beyond `dump(mode: str) -> dict`
- Changing the read path (`model=` parameter) in any way
- Adding alma_models as a dependency — the coupling is structural only

## Decisions

### 1. Runtime-checkable Protocol for duck typing

Use `@runtime_checkable class Dumpable(Protocol)` with a single method `dump(self, mode: str = ...) -> dict[str, Any]`.

**Why over alternatives:**
- `isinstance(x, BaseModel)` — couples to Pydantic, excludes non-Pydantic implementations
- `hasattr` check — no static type safety, IDE can't infer
- ABC / base class — requires alma_models to inherit from almapy, wrong dependency direction

Protocol gives both static checking (mypy/pyright see the union) and runtime dispatch (isinstance in execute).

### 2. Conversion in `execute()`, before the retry loop

The `json=` kwarg arrives via `**kwargs`. Check and convert once before `stamina.retry_context`:

```python
if "json" in kwargs and isinstance(kwargs["json"], Dumpable):
    kwargs["json"] = kwargs["json"].dump(mode="json")
```

**Why here:**
- Single conversion point — every `_put`, `_post`, `_delete` benefits
- Before retry loop — dump runs once, not per-attempt
- After this line, the rest of execute sees a plain dict as before

### 3. `mode="json"` passed explicitly

alma_models' `dump()` defaults to `mode="json"`, but almapy passes it explicitly. This makes the serialization contract visible in almapy's code and resilient to upstream default changes.

### 4. `Body` type alias for signatures

```python
Body = dict[str, Any] | Dumpable
```

Public namespace methods change `dict[str, Any]` to `Body` for body parameters. This surfaces model support in IDE autocomplete without making signatures noisy.

### 5. Explicit `model=` required — no auto-inference of return type

When a `Dumpable` body is passed, the return type is NOT automatically inferred from the body type. The user must still pass `model=` explicitly to get a typed response, same as on the read path. This keeps the API consistent: `model=` always means the same thing regardless of method.

The existing two-overload pattern per write method stays unchanged in shape — just `dict[str, Any]` becomes `Body`:

```python
@overload
async def update_user(self, user_id: str, user: Body, *, model: type[_ModelT]) -> _ModelT: ...
@overload
async def update_user(self, user_id: str, user: Body, *, model: None = ...) -> RESP_TYPE: ...
```

When the user passes both a typed body and `model=`, the `_ModelT` TypeVar links them — mypy verifies input and output are the same type.

**Why not auto-infer:** Auto-inference would mean some methods need `model=` (reads) and others don't (writes with a typed body). That inconsistency is worse than the small repetition of stating the type twice.

### 6. Protocol lives in `_utils.py`

`_utils.py` already hosts `RESP_TYPE`, `_ModelT`, and `Request`. It's the established home for shared type definitions.

## Risks / Trade-offs

- **Name collision on `dump()`**: Any object with a `dump(mode)` method would be auto-converted. This is intentional — the Protocol is the contract — but could surprise if an unrelated object happens to match. Mitigation: the method name + signature is specific enough that accidental matches are unlikely.
- **Protocol `isinstance` checks attribute existence, not return type**: At runtime, an object with `dump` returning non-dict would pass the isinstance check and fail at serialization time. Mitigation: this is a general Protocol limitation; the static type checker catches mismatches at the call site.
