## ADDED Requirements

### Requirement: Primo search namespace

`AlmaClient` SHALL expose a `primo` namespace whose `search(...)` method issues a `GET` request to the Primo Search API (`/primo/v1/search`) on the same regional gateway and with the same API key as Alma requests.

#### Scenario: Namespace is available on the client

- **WHEN** an `AlmaClient` is constructed
- **THEN** `client.primo` is an instance of the Primo namespace exposing an awaitable `search(...)` method

#### Scenario: Request targets the Primo base path on the correct region

- **WHEN** `client.primo.search(...)` is called on a client configured for a given region
- **THEN** the request is sent to that region's gateway host with the `/primo/v1/search` path (not Alma's `/almaws/v1`)
- **AND** the request carries the same `Authorization: apikey <key>` header used for Alma requests

### Requirement: Required search parameters

`search(...)` SHALL require the Primo-mandated query parameters `q`, `vid`, `tab`, and `scope`, and SHALL send them as query parameters on the request.

#### Scenario: Required parameters are forwarded

- **WHEN** `search(q="any,contains,dickens", vid="V", tab="T", scope="S")` is called
- **THEN** the request query string includes `q=any,contains,dickens`, `vid=V`, `tab=T`, and `scope=S`

### Requirement: Optional search parameters with API-aligned defaults

`search(...)` SHALL accept the optional Primo parameters as keyword arguments, applying the Primo API's documented defaults when the caller omits them. Parameters whose value is `None` SHALL be omitted from the request.

#### Scenario: Defaults match the Primo API

- **WHEN** `search(...)` is called with only required parameters
- **THEN** `limit` defaults to 10, `offset` to 0, `sort` to `rank`, and `lang` to `eng`

#### Scenario: Omitted optional parameters are not sent

- **WHEN** `search(...)` is called without `q_include`, `from_date`, or `personalization`
- **THEN** the request query string contains no `qInclude`, `fromDate`, or `personalization` keys

#### Scenario: Sort accepts only the documented values

- **WHEN** `sort` is supplied
- **THEN** the accepted values are constrained to `rank`, `title`, `author`, `date`, `date_d`, and `date_a`

### Requirement: Snake_case keyword arguments map to camelCase wire names

`search(...)` SHALL accept Python-idiomatic snake_case keyword arguments and translate them to the camelCase query-parameter names the Primo API expects.

#### Scenario: Keyword names are translated for the wire

- **WHEN** `search(..., q_include="facet_rtype,include,books", from_date="20240101000000", newspapers_search=True)` is called
- **THEN** the request query string uses the keys `qInclude`, `fromDate`, and `newspapersSearch`

### Requirement: Box-wrapped response with optional model validation

`search(...)` SHALL return the parsed JSON response wrapped for dot-notation access, and SHALL accept an optional `model=` keyword that, when given a Pydantic model class, returns the validated model instead.

#### Scenario: Default returns a Box

- **WHEN** `search(...)` is called without `model=`
- **THEN** the return value supports dot-notation access to the response fields

#### Scenario: model= returns a validated instance

- **WHEN** `search(..., model=SomeModel)` is called
- **THEN** the response is validated through `SomeModel.model_validate(...)` and the typed instance is returned

### Requirement: Shared transport and error handling

Primo search requests SHALL reuse `AlmaClient`'s existing throttle, retry, concurrency, and backpressure machinery. `AlmaClient.execute()` SHALL accept an optional `validate=` callable, defaulting to the existing Alma response validator, so Primo-specific error handling can be supplied without changing Alma behaviour.

#### Scenario: Existing Alma calls are unaffected

- **WHEN** an existing Alma namespace method calls `execute()` without `validate=`
- **THEN** the Alma response validator is used exactly as before

#### Scenario: Primo errors raise mapped exceptions

- **WHEN** a Primo search request returns an error status (e.g. 401 or 500)
- **THEN** `search(...)` raises an almapy exception consistent with the existing exception hierarchy rather than returning the raw error body
