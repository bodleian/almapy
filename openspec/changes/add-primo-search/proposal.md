## Why

almapy currently wraps only the Alma APIs, but the same regional Ex Libris gateway and the same API key also expose the Primo Search API (`GET /primo/v1/search`). Consumers who want discovery-layer search results today must hand-roll a second HTTP client with its own throttling and retry logic. Surfacing Primo search through the existing `AlmaClient` lets callers reuse the client they already configure — same key, same rate budget, same backpressure — with one extra namespace.

## What Changes

- Add a `client.primo` namespace exposing `search(...)`, mapping the full Primo Search query-parameter set (`q`, `vid`, `tab`, `scope`, paging, sort, facets, language, and the boolean toggles) onto explicit named keyword arguments, following the existing `bibs.get_items` house style (named params, `Literal` enums, the `model=` overload triple, Box-wrapped JSON responses).
- Stash the regional gateway root on `AlmaClient` so the Primo namespace can target the `/primo/v1` base path (distinct from Alma's `/almaws/v1`) without disturbing the Alma session's `base_url`.
- Add an optional `validate=` parameter to `AlmaClient.execute()` defaulting to the existing Alma response validator, giving the Primo namespace a seam to plug in Primo-specific error handling if live responses prove to use a different error-body shape than Alma's `errorList` envelope.

No breaking changes — Alma behaviour is unchanged; all additions are additive.

## Capabilities

### New Capabilities
- `primo-search`: Issue Primo discovery searches through `AlmaClient`, reusing the shared API key, throttle, retry, and backpressure infrastructure, with results wrapped for dot-notation access and optional Pydantic model validation.

### Modified Capabilities
<!-- None: no existing spec-level behaviour changes. The execute() validate= seam is an additive, backward-compatible signature change covered under the new capability's design. -->

## Impact

- **New code**: `src/almapy/_primo.py` (`AlmaClientPrimoNS`), `tests/test_primo.py`.
- **Modified code**: `src/almapy/_client.py` (stash `_gateway` root, wire `self.primo`, add `validate=` kwarg to `execute()`); `src/almapy/_base.py` (`_AlmaExecutable` protocol gains the `validate=` kwarg); optionally `src/almapy/_endpoints.py` (a `PRIMO_SEARCH` path constant).
- **APIs**: New public surface `client.primo.search(...)`. `AlmaClient.execute()` gains a backward-compatible optional `validate=` keyword.
- **Dependencies**: None added — reuses `niquests`, `box`, `stamina`.
- **Verification unknowns** (resolved during implementation against one live call): (1) whether niquests' `base_url` join uses RFC-3986 resolution or naive concatenation, which determines whether an absolute URL is required; (2) the actual shape of Primo error bodies (gateway-level vs application-level), which determines whether the `validate=` seam ships with a custom Primo validator or defers to the Alma default.
