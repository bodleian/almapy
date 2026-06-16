## 1. Transport seams in AlmaClient

- [x] 1.1 In `AlmaClient.__init__` (`_client.py`), stash the gateway root as `self._gateway = _LOCATIONS[location]` (before the `/almaws/v1` suffix is appended to `base_url`).
- [x] 1.2 Add an optional `validate: Callable[[niquests.Response], None] = _validate_response` keyword to `AlmaClient.execute()` and call `validate(resp)` in place of the hardcoded `_validate_response(resp)`.
- [x] 1.3 Update the `_AlmaExecutable` protocol in `_base.py` to include the optional `validate=` keyword on `execute()` so namespaces type-check.
- [x] 1.4 Confirm existing Alma calls still pass `mypy --strict` and run unchanged (default `validate`).

## 2. Primo namespace

- [x] 2.1 Create `src/almapy/_primo.py` with `AlmaClientPrimoNS(BaseNamespace)`.
- [x] 2.2 (Optional) Add `PRIMO_SEARCH = "/primo/v1/search"` to `_endpoints.py`, or build the path inline in the namespace.
- [x] 2.3 Implement `search(...)` with required params `q`, `vid`, `tab`, `scope` and optional params (`limit=10`, `offset=0`, `sort` as a `Literal` defaulting to `rank`, `lang="eng"`, `q_include`, `q_exclude`, `multi_facets`, `from_date`, `personalization`, `journals`, `databases`, `con_voc=True`, `skip_delivery=True`, `disable_split_facets=True`, `newspapers_search=False`, `pc_availability=True`).
- [x] 2.4 Build the `params` dict mapping snake_case kwargs to camelCase wire keys (`q_include`→`qInclude`, `from_date`→`fromDate`, etc.); rely on niquests dropping `None` values.
- [x] 2.5 Build the absolute URL `f"{self._client._gateway}/primo/v1/search"` and call `execute("GET", url, parser="json", params=params, model=model)`.
- [x] 2.6 Add the `model=` overload triple (`type[_ModelT]` / `None` / `Any`) matching the `bibs.get_items` pattern.

## 3. Wiring

- [x] 3.1 Import `AlmaClientPrimoNS` in `_client.py` and assign `self.primo = AlmaClientPrimoNS(self)` alongside the other namespaces.
- [x] 3.2 Export anything that belongs in the public API surface (mirror how other namespaces are exported, if applicable). — Namespaces are not exported in `__init__.py`; reached via `client.primo`, mirroring `users`/`bibs`/etc.

## 4. Verification against live behaviour

- [x] 4.1 Confirm niquests sends the absolute Primo URL correctly (host + `/primo/v1/search`, not joined onto `/almaws/v1`). — Verified deterministically via `tests/test_primo.py::TestRequestRouting` (mocked adapter records host `api-eu...` + path `/primo/v1/search`).
- [~] 4.2 Inspect a live Primo error response (401 and/or 500) and decide whether the Alma default validator handles it or a Primo-specific `validate=` callable is needed; implement the custom validator only if the body shape diverges from Alma's `errorList` envelope. — Deferred: requires a live API key (not available in this env). Per the design's conditional, `search()` defaults to the Alma `_validate_response` validator; the `validate=` seam is wired and ready so a Primo-specific validator is a one-line addition once a live error body is observed.

## 5. Tests

- [x] 5.1 Add `tests/test_primo.py` asserting the namespace exists on the client and `search(...)` is awaitable.
- [x] 5.2 Test that required params and a representative set of optional params are forwarded with correct camelCase keys, and that omitted optional params are absent from the query string.
- [x] 5.3 Test that defaults (`limit`, `offset`, `sort`, `lang`) match the Primo API documented values.
- [x] 5.4 Test the `model=` path validates the response through the supplied model.
- [x] 5.5 Run `just lint` and `just test`; ensure doctest/typeguard checks pass and coverage stays above the 50% minimum. — Full suite: 129 passed, 4 skipped (doctest-modules + typeguard active). New files pass `ruff format --check`, `ruff check`, and `mypy`. NOTE: repo-wide `just lint` surfaces two **pre-existing** issues unrelated to this change — a mypy error in `_config.py::get_departments` (committed in `dba18ea`) and a deptry `DEP002 urllib3-future` warning.
