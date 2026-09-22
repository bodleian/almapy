# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [9.3.1] - 2026-09-22

### Fixed
- **endpoints**: keep the slash in a PO line number – Alma addresses `204029292/0005` with the slash raw, and encoding it to `%2F` made the Ex Libris gateway refuse the request before Alma saw it

## [9.3.0] - 2026-09-21

### Added
- **bibs**: digital representations at `client.bibs.representations` – list, create, update and delete Alma Digital representations and their files
- **exceptions**: `BibNotInCollectionError` for Alma error 402260, raised when creating a representation on a bib that belongs to no collection

## [9.2.1] - 2026-09-15

### Fixed
- **client**: an injected niquests session now asks Alma for JSON – niquests seeds new sessions with `Accept: */*`, which `setdefault` left in place, so Alma answered every JSON endpoint in XML

### Build
- **release**: drive the GitHub Release notes from CHANGELOG.md

### Documentation
- **changelog**: reconcile the 9.2.0 section

## [9.2.0] - 2026-09-15

### Added
- **client**: raise `MalformedResponseError`, a retryable `APIServerError`, when a 2xx body cannot be parsed as the promised JSON or XML or arrives as HTML – previously niquests' own `JSONDecodeError` escaped with no status, content type or body, and was neither retried nor counted as backpressure

### Fixed
- **utils**: an error body under an XML content type that is not well-formed XML now raises the status-appropriate almapy error instead of a bare `ExpatError`

## [9.1.3] - 2026-09-14

### Fixed
- **bibs**: stop sending override_warning=false on default create and update – Alma rejects it unless validate or check_match is also set (error 401873), so every plain create_bib and update_bib call failed

## [9.1.2] - 2026-08-03

### Documentation
- **exceptions**: show the exception hierarchy on the reference page
- **throttle**: write the rate-limiting classes for consumers
- move the Alma link from the docstring foot to the method heading
- link each method to its Ex Libris endpoint documentation
- **users**: drop the user-identifier note
- **client**: explain what execute is for, and surface retry in its signature
- link the docs site from the README, and fix the model= example
- add a Zensical site with a generated API reference
- fix a malformed Attributes entry on CannotRenewError
- **throttle,utils**: document the backpressure controls and body protocols
- **bibs**: document bib, holding, loan and request namespaces
- **users**: document loan, fine and request namespaces
- **config**: document set, library, letter, job and code-table namespaces
- **acq,analytics**: document namespace methods

### Style
- use en dashes throughout, and declare the convention

### Other
- **deps**: declare griffe for the docs extension
- **deps**: lock the docs dependency group
- build the docs on PRs and publish them to GitHub Pages

### Fixed
- **types**: make Dumpable and ModelDumpable mode keyword-only
- **types**: accept any Body on sets.create and jobs.submit_job

## [9.1.1] - 2026-07-29

### Fixed
- **throttle**: make recovery gating independent of the monotonic epoch

## [9.1.0] - 2026-07-29

### Style
- use ruff rule names instead of codes

### Other
- **deps**: refresh the lockfile
- pin setup-uv to an existing ref
- add lint, test matrix and build workflow
- untrack the openspec working directory
- **release**: publish to PyPI via Trusted Publishing

### Tests
- close the gaps that let the barcode parser ship broken
- add local version matrix and a wheel smoke test

### Fixed
- **endpoints**: percent-encode path parameters
- **analytics**: coerce single-element results from xmltodict
- **errors**: survive non-JSON bodies and make exceptions robust
- **client**: configure a session passed via client=
- **logging**: stop mutating global logging and stamina state on import

### Build
- drop the internal GitLab publish-url

### Documentation
- document typed request bodies, drop the alma_models section

### Added
- **client**: accept pydantic models as request bodies
- **packaging**: add MIT licence and complete the PyPI metadata

## 9.0.0 (2026-07-28)

### BREAKING CHANGE

- bibs.delete_bib(override), bibs.update_bib(override_warning),
bibs.update_bib(override_lock) and bibs.create_bib(override_warning) now
default to False. Pass the flag explicitly to restore the previous behaviour.
- writes are no longer retried on timeouts, connection errors or
server errors. Pass retry=True to restore the previous behaviour.

### Fix

- **bibs**: correct create_bib CZ parameter and stop overriding by default
- **client**: do not replay non-idempotent writes on ambiguous failures
- **build**: keep integration credentials and patron data out of the sdist

## 8.4.0 (2026-06-24)

### Feat

- **bibs**: wrap bib-level request endpoints; migrate tests to niquests-mock
- accept Dumpable model objects as write method bodies
- **primo**: add Primo Search namespace
- add get_departments method

### Fix

- **http**: pass raw write bodies via data= for niquests
- **logging**: suppress stamina retry_scheduled log even when hooks re-enabled
- **config**: type get_departments params and tidy lint config
- disable stamina's built in retry logging
- **logging**: remove throttle noise, sanitize URLs, suppress urllib3 debug

## 8.0.0 (2026-03-30)

### Feat

- **tests**: add NiquestsMock infrastructure and rsps fixture
- **client**: replace httpx with niquests as HTTP transport
- **logging**: add structured fields to all log extra dicts

## 7.0.0 (2026-03-26)

### Feat

- **_utils**: add almapy.error logging for error parsing events
- **_throttle**: add almapy.throttle logging for rate limiting events
- **_client**: add almapy.http and almapy.retry logging with per-request correlation IDs
- **_logging**: add shared logging infrastructure with per-request correlation IDs
- **exceptions**: add public AlmapyError root exception

## 6.0.0 (2026-03-25)

### Feat

- **_acq**: add model= overloads to all 3 Box-returning acq namespace methods
- **_config**: add model= overloads to all 26 Box-returning config namespace methods
- **_bibs**: add model= overloads to all 20 Box-returning bib namespace methods
- **_users**: add model= overloads to all 19 Box-returning user namespace methods
- **deps**: remove gracy, export ThrottleTimeoutError
- **namespaces**: migrate all namespace files from GracyNamespace to BaseNamespace
- **_client.py**: rewrite as composed AlmaClient without gracy
- **_base.py**: add BaseNamespace replacing GracyNamespace
- **_endpoints.py**: remove gracy dependency, add build() with strict validation

### Fix

- **_client**: only record_failure for retryable exceptions
- **_throttle**: raise ThrottleTimeoutError on max_wait exceeded

### Refactor

- **_users,_acq,_bibs,_config**: deletion methods return None instead of bool
- **_client,_base**: text parser returns str directly instead of Box
- **_client**: move _parse back into AlmaClient as @staticmethod
- **_base**: remove __slots__ and noqa suppression
- **_client**: semaphore per-attempt; remove _raw_request
- **exceptions**: extract _AlmaError base; document two-tier pattern
- **_utils**: flatten to _raise_for_error_body; add XML + glom-failure tests
- **_client**: wire _should_retry into stamina
- **exceptions**: ThresholdError → APIClientError; explicit _RETRYABLE
- **_utils**: rename process_response → _process_response
- **_utils**: remove AlmaErrorValidator compatibility shim

## 5.28.0 (2025-10-14)

### Feat

- **exceptions.py**: add UserIsNotAPatronError

## 5.27.7 (2025-10-08)

### Fix

- **_users.py**: fix type checking bug

## 5.27.6 (2025-10-01)

### Fix

- **AlmaClient**: disable gracy log propagation and tweak retry log messages

### Refactor

- up minimum python to 3.11

## 5.27.5 (2025-09-30)

### Fix

- **AlmaClientUserFinesNS**: take floats for fee amounts

## 5.27.4 (2025-09-30)

### Fix

- **AlmaClientUserFinesNS**: fix update_fee

## 5.27.3 (2025-09-25)

### Fix

- **AlmaClient**: retry on httpx.ReadError

## 5.27.2 (2025-09-12)

### Fix

- **AlmaClientUserFinesNS**: fix missing user_id parameter in get_fee

## 5.27.1 (2025-09-12)

### Fix

- **AlmaClientUserNS**: alias users.fines as users.fees

## 5.27.0 (2025-09-12)

### Feat

- **AlmaClientUserFinesNS**: add remaining fine/fee methods

## 5.26.0 (2025-08-29)

### Feat

- **bibs**: add update_request method

## 5.25.0 (2025-08-15)

### Feat

- **exceptions.py**: add CannotBeLoanedError

## 5.24.0 (2025-06-11)

### Feat

- **config**: add integration profile methods
- **bibs**: add delete_bib and update_bib

### Fix

- **AlmaClient**: retry GracyParseFailed
- **bibs**: fix update_bib and delete_bib endpoints

## 5.21.0 (2025-03-12)

### Feat

- **bibs**: add get_holdings

## 5.20.2 (2025-02-26)

### Fix

- **_config.py**: fix sets.create and sets.manage_members

## 5.20.1 (2025-02-07)

### Fix

- fix assert_never breakage <3.11

## 5.20.0 (2025-01-27)

### Feat

- **exceptions**: add IllegalBarcodeError

## 5.19.0 (2025-01-15)

### Feat

- **exceptions**: add ItemAlreadyLoanedToUserError

### Fix

- **utils**: include HTTP 401 in APIClientError handling
- **analytics**: fix deprecated gracy decorator
- **exceptions**: fix POUpdateFailedError

## 5.18.0 (2024-10-14)

### Feat

- **exceptions**: add ExpiredCardError
- **exceptions.py**: add LoanNotFoundError

### Fix

- **users**: fix get_fines TypeError
- **exceptions**: fix LoanNotFoundError

## 5.17.0 (2024-09-20)

### Feat

- **config**: add code table endpoints

### Fix

- **utils**: fix 'NoneType is not iterable' on 504 (hopefully)

### Refactor

- typing changes
- **AlmaClient**: tweak retries and limits

## 5.16.0 (2024-08-01)

### Feat

- **users**: raise a UserNotFoundError in any method

## 5.15.0 (2024-07-04)

### Feat

- **exceptions**: add MMSIdNotFoundError
- **exceptions**: add API error code to exception message

### Fix

- **users**: change_loan_due_date now uses PUT instead of GET

## 5.14.0 (2024-06-03)

### Feat

- **exceptions**: add POUpdateFailedError

### Fix

- **config**: fix submit_job

## 5.13.0 (2024-05-23)

### Feat

- **config**: add jobs methods

### Fix

- **client**: handle HTTP 403 as APIClientError

## 5.12.0 (2024-05-17)

### Feat

- **exceptions**: add ParallelRequestError

### Fix

- **bibs**: put methods back in namespace

## 5.11.0 (2024-05-09)

### Feat

- **bibs**: add delete_holding and withdraw_item methods

### Perf

- **client**: increase starting (and therefore all subsequent) retry delays

## 5.10.0 (2024-05-03)

### Feat

- **users**: add cancel_request method
- **users**: add get_requests method
- **bibs**: add create_item and create_bib methods

### Fix

- **bibs**: fix create_bib Content-Type

### Refactor

- add py.typed

## 5.9.0 (2024-02-29)

### Feat

- **exceptions**: add NoItemsCanFulfillRequestError

### Refactor

- **AlmaClient**: remove logging of concurrent request limit

## 5.8.0 (2024-02-22)

### Feat

- **users**: add create_user_attachment method

## 5.7.0 (2024-02-21)

### Feat

- **acq**: add update_po_line method

## 5.6.0 (2024-02-02)

### Feat

- **acq**: add cancel_po_line method
- **acq**: add receive_existing_item method

### Fix

- **analytics**: fix error when report only has one row
- **AlmaClient**: fix retries for rate limit errors
- **acq**: fix receive_existing_item using GET instead of POST
- **analytics**: fix error when report has no rows
- **acq**: fix po line item endpoint

## 5.5.0 (2024-01-23)

### Feat

- **bibs**: add get_requests_for_bib and get_request methods, and get_requests_for_item alias for get_requests

### Fix

- **bibs**: fix create_holding parsing
- **bibs**: fix create_holding endpoint

## 5.4.0 (2024-01-16)

### Feat

- **AlmaClient**: improve exception handling
- **bibs**: add get_bib method

### Refactor

- **AlmaClient**: retry more timeout exceptions

## 5.3.0 (2024-01-08)

### Feat

- **bibs**: add get_item_by_pid method

### Fix

- **_endpoints.py**: fix PO_LINE endpoint

## 5.2.0 (2023-12-21)

### Feat

- **exceptions**: add ScanItemRetrievalError (402504)
- **AlmaClient**: add concurrent_requests param and up timeout to 60
- **users**: add get_users

### Fix

- **AlmaClient**: retry all timeouts
- **AlmaClient**: retry httpx.ReadTimeout
- **analytics**: fix broken endpoint and resumption token
- fix POST body params
- **bibs**: fix default None params
- **AlmaEndpoint**: fix set member endpoint
- **AlmaClient**: add back analytics namespace (oops)
- **AlmaClient**: tweak limits
- **AlmaClient**: raise pool limits to prevent PoolTimeout
- **users**: fix expand param for get_users
- **users**: add default for order_by in get_users

## 5.1.1 (2023-12-11)

### Fix

- **_handle_utils**: fix custom exception use

## 5.1.0 (2023-12-06)

### Feat

- **AlmaClient**: allow specifying per-second ratelimit via rate_limit param

### Fix

- **AlmaClient**: follow redirects (for barcode lookup)

## 5.0.1 (2023-12-05)

### Fix

- **_client.py**: set httpx logging level to critical
- **AlmaClient**: fix user -> users namespace

### Refactor

- **AlmaClient**: tweaks to timeout, retries

## 5.0.0 (2023-12-05)

### BREAKING CHANGE

- AlmaClient is no longer used as a context manager. XML support dropped entirely, apart from endpoints where it makes more sense than JSON.

### Feat

- total rewrite to use gracy under the hood

## 4.11.0 (2023-11-27)

### Feat

- **bibs.py**: add create_holding method

## 4.10.0 (2023-11-22)

## 4.9.0 (2023-11-13)

### Feat

- **users.py**: add update_request method

## 4.8.0 (2023-10-20)

### Feat

- **users.py**: add users.request.create_request method

## 4.7.1 (2023-10-16)

### Fix

- **__init__.py**: fix self.acq namespace

## 4.7.0 (2023-10-16)

### Feat

- **acq.py**: add acq client and acq.get_po_line
- **bibs.py**: add bibs.requests.create_request method
- **users.py**: throw UserNotFoundError for get_loans

### Fix

- **bibs.py**: fix create_request

## 4.6.0 (2023-10-05)

### Feat

- **users,utils**: add UserNotFoundError exception

## 4.5.0 (2023-10-03)

### Feat

- **bibs.py**: add bibs.requests.cancel_request an bibs.requests.get_requests

### Refactor

- **utils.py**: print response body of unknown errors

## 4.4.2 (2023-09-28)

### Fix

- **utils.py**: handle weird XML server errors with generic exceptions

## 4.4.1 (2023-09-27)

### Refactor

- **utils.py**: add debug statements for unexpected xml

## 4.4.0 (2023-09-19)

### Feat

- **users.py**: add create_user method

## 4.3.1 (2023-09-01)

### Fix

- **client.py**: retry RemoteProtocolError

## 4.3.0 (2023-08-01)

### Feat

- **client.py**: add jitter to retries

### Fix

- **utils.py**: raise LoanBlockedError for loan failures due to cash limits

## 4.2.3 (2023-06-29)

### Fix

- **bibs.py**: fix exception string

## 4.2.2 (2023-06-29)

### Fix

- **bibs.py**: fix RequestFailedError regex

## 4.2.1 (2023-06-29)

### Fix

- **utils.py**: use InvalidFieldError

## 4.2.0 (2023-06-29)

### Feat

- **exceptions.py**: add specific exceptions for invalid item fields

## 4.1.0 (2023-06-28)

### Feat

- **users.py**: add notify_user param to change_loan_due_date

### Fix

- **Client,AlmaClient**: retry httpx.ConnectTimeout, add httpx trasnport retries, and up retry count and wait times

## 4.0.0 (2023-05-22)

### Feat

- **bibs.py**: add update_item method

### Fix

- **utils.py**: strip leading whitespace from server errors

### Refactor

- **exceptions.py**: make APIServerError inherit from Exception, rather than APIClientError

## 3.1.1 (2023-04-17)

### Fix

- **client.py**: retry ThresholdError

## 3.1.0 (2023-04-14)

### Feat

- **client.py**: add call logging

## 3.0.0 (2023-04-13)

### Feat

- **config.py**: add location methods to config.libraries

### Fix

- **client.py**: make post requests respect rate limit

## 2.3.0 (2023-03-29)

### Feat

- **bibs.py**: add scan_in method

## 2.2.0 (2023-03-20)

### Feat

- **config.py**: add manage_members set method

## 2.1.0 (2023-03-10)

### Feat

- **exceptions.py**: add LoanBlockedError

## 2.0.1 (2023-03-09)

### Fix

- **__init__.py**: fix import error

## 2.0.0 (2023-03-08)

### BREAKING CHANGE

- exceptions moved from almapy.utils to almapy.exceptions

### Feat

- **exceptions.py**: move exceptions and add LoanLimitError

## 1.1.0 (2023-03-02)

### Feat

- **analytics.py**: add Analytics

## 1.0.3 (2023-02-23)

### Fix

- **__init__.py,users.py,client.py,utils.py**: fix bodyless post, exception changes, follow redirects

### Refactor

- **pypoetry.toml**: bump deps

## 1.0.2 (2023-02-20)

### Fix

- **users.py**: fix create_loan method

## 1.0.1 (2023-02-20)

### Fix

- **users.py**: fix create_loan method

### Refactor

- use glom for server error -> exception mungeing

## 1.0.0 (2023-02-17)

### BREAKING CHANGE

- rename exception classes

### Feat

- add retries and change exceptions

## 0.2.0 (2023-02-17)

### Feat

- **users.py**: add users.requests and get_request method

### Fix

- **client.py**: fix inconsistencies between methods for xml/json handling

## 0.1.0 (2023-02-16)

### Feat

- **users.py**: add request_id param

## 0.0.5 (2023-02-16)
