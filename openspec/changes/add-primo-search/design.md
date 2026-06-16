## Context

`AlmaClient` (`_client.py`) is a composed async client: a `niquests.AsyncSession` with `base_url = {region_gateway}/almaws/v1` and an `Authorization: apikey <key>` header, plus a `TokenBucket`, an `AdaptiveController` (AIMD backpressure), and a concurrency semaphore. Functional namespaces (`users`, `bibs`, `acq`, `config`, `analytics`) subclass `BaseNamespace`, build URLs, and delegate to `AlmaClient.execute()`, which runs the stamina retry loop, acquires throttle/concurrency, calls `_validate_response()` (the Alma `errorList`-envelope error mapper in `_utils.py`), and wraps the body in a `Box`.

The Primo Search API (`GET /primo/v1/search`) lives on the **same** regional gateways and is reachable with the **same** API key. It differs from Alma on only two axes: the base path (`/primo/v1` vs `/almaws/v1`) and a potentially different error-body shape. The throttle, retry, concurrency, auth header, and Box-wrapping are all reusable as-is.

## Goals / Non-Goals

**Goals:**
- Expose `client.primo.search(...)` reusing the existing transport, throttle, retry, and backpressure.
- Match almapy's house style (`bibs.get_items`): explicit named kwargs, `Literal` enums, the `model=` overload triple, Box responses.
- Keep all Alma behaviour byte-for-byte unchanged; additions are additive.

**Non-Goals:**
- No query-builder/DSL helper for the `q` string — it is passed raw, exactly as Alma's own `q` parameter is (consistency with `bibs.get_items`).
- No Primo endpoints beyond search in this change.
- No separate `PrimoClient` class or transport refactor — the shared key makes a namespace the right shape.
- No separate throttle bucket for Primo (see Open Questions).

## Decisions

### Namespace on `AlmaClient`, not a separate client
The shared API key and shared regional gateway remove the only strong argument for a peer client. A namespace reuses `execute()` wholesale and matches how every other API area is exposed. Alternative considered: a standalone `PrimoClient` or an extracted transport core — rejected as unnecessary churn given there is no separate key, base host, or rate budget to isolate.

### Target `/primo/v1` via an absolute URL built from a stored gateway root
The session's `base_url` ends in `/almaws/v1`, so Primo requests cannot ride it. `AlmaClient.__init__` will stash `self._gateway = _LOCATIONS[location]` (the host root, before the `/almaws/v1` suffix). The Primo namespace builds an absolute URL `f"{client._gateway}/primo/v1/search"` and passes it to `execute()`, which forwards an arbitrary `url` straight to `niquests`. An absolute URL is unambiguous regardless of how niquests merges `base_url`.

Alternative considered: passing a leading-slash path (`/primo/v1/search`) and relying on RFC-3986 resolution to replace `/almaws/v1`. Rejected as dependent on unverified niquests join semantics; the absolute URL sidesteps the question.

### Pluggable `validate=` seam on `execute()`
`execute()` hardcodes `_validate_response(resp)`. We add a keyword `validate: Callable[[Response], None] = _validate_response`. Alma callers are unchanged (default). The Primo namespace can pass a Primo-specific validator if live error bodies differ from Alma's `errorList` envelope. The `_AlmaExecutable` protocol in `_base.py` gains the same optional kwarg.

Day one, Primo may default to the Alma validator: if Primo's 401/500 come from the gateway layer they likely share Alma's `errorList` envelope. The seam exists so a custom validator is a localized change, not a refactor.

### snake_case kwargs → camelCase wire names
Primo params are camelCase (`qInclude`, `fromDate`, `newspapersSearch`); almapy kwargs are snake_case everywhere else. `search()` assembles a `params` dict mapping each supplied kwarg to its camelCase wire key. `None`-valued params are dropped automatically by niquests, so optional params need no guards. Booleans are forwarded as Python `bool` — the API normalizes `True`/`False` correctly, so no string coercion is needed.

## Risks / Trade-offs

- **Primo error bodies may not match Alma's `errorList` envelope** → If they differ, the default validator would funnel a 401 into a generic `APIServerError("Unknown error")`, misclassifying a 4xx and dropping the message. Mitigation: the `validate=` seam lets us drop in a Primo validator once a live error body is observed; covered by a task to verify against one live call.
- **niquests `base_url` join semantics unverified** → Mitigation: building a fully-absolute URL with host makes the merge behaviour irrelevant.
- **Shared rate budget** → Primo search traffic draws from the same `TokenBucket`/AIMD controller as Alma. Acceptable and arguably correct given a single key's quota, but heavy Primo use will throttle Alma calls and vice versa (see Open Questions).

## Open Questions

- **Should Primo get its own throttle bucket?** Currently it shares Alma's. A single shared budget matches a single key's quota, but callers hammering Primo discovery alongside Alma traffic will contend. Deferred unless real usage shows contention; revisiting would mean parameterizing the controller per base path.
- **Custom Primo validator on day one or deferred?** Resolved by the verification task — inspect a live Primo 401/500 body; ship a custom validator only if the shape diverges from Alma's `errorList`.
