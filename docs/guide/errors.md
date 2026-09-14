# Errors

## The hierarchy

Every exception almapy raises descends from `AlmapyError`, so one `except`
clause catches anything originating in the library:

```
AlmapyError
├── ThrottleTimeoutError        (also a TimeoutError)
└── _AlmaError
    ├── APIServerError          5xx, or an unusable 2xx body – Alma's fault, retried automatically
    │   └── MalformedResponseError
    └── APIClientError          4xx – your request, not retried
        ├── ThresholdError      429 – rate limit exceeded
        ├── BarcodeNotFoundError
        ├── UserNotFoundError
        ├── LoanLimitError
        └── ... 20 more
```

The split that matters in practice is `APIServerError` versus
`APIClientError`. A server error has already been retried three times before it
reaches you, so seeing one means Alma is genuinely unwell. A client error means
the request itself was wrong and retrying will not help.

`MalformedResponseError` is the one server error that does not come from a 5xx:
Alma, or a gateway in front of it, answered 2xx with a body that is not the JSON
or XML the endpoint promised – an HTML maintenance page, say. Its `code` is the
HTTP status and its message carries the content type and a short excerpt of the
body. It has no Alma error code, so it does not appear in the table below. Like
any other 5xx it is not replayed for POST or PATCH: Alma may well have applied
the write before the response was mangled.

```python
from almapy.exceptions import APIClientError, APIServerError

try:
    item = await client.bibs.get_item(barcode)
except APIServerError:
    logger.warning("Alma is struggling; will pick this up in the next run")
except APIClientError as exc:
    logger.error("Bad request for %s: %s", barcode, exc)
```

## Catching specific failures

Alma reports failures as numeric codes in the response body. almapy parses those
and raises a specific class, so you can branch on the failure rather than
string-matching a message:

```python
from almapy.exceptions import BarcodeNotFoundError, LoanBlockedError, LoanLimitError

try:
    loan = await client.users.loans.create_loan(
        user_id, barcode, circ_desk="DEFAULT", library="MAIN"
    )
except LoanLimitError:
    print("Patron is at their loan limit")
except LoanBlockedError as exc:
    print(f"Blocked: {exc.error}")
except BarcodeNotFoundError:
    print("No such item")
```

Unmapped codes still raise – as the status-appropriate `APIClientError` or
`APIServerError` – so nothing is swallowed.

## What is on an exception

Handler-raised exceptions carry Alma's own code and message:

```python
except APIClientError as exc:
    exc.code       # "401689" – Alma's numeric error code
    exc.error      # Alma's raw message
    exc.message    # "<message> [<code>]"
    str(exc)       # same as .message
```

Some exceptions are enriched by the namespace method that caught them, adding
domain context – `UserMissingFieldError` carries the user ID it was raised for,
`CannotRenewError` the loan ID, `InvalidCodeError` the field and value Alma
rejected.

## Error codes almapy maps

| Alma code | Exception |
|---|---|
| `400042` | `ItemAlreadyLoanedToUserError` |
| `401129` | `NoItemsCanFulfillRequestError` |
| `401136` | `ParallelRequestError` |
| `401151` | `UserIsNotAPatronError` |
| `401153` | `CannotBeLoanedError` |
| `401161` | `LoanLimitError` |
| `401163`, `401201` | `LoanBlockedError` |
| `401168` | `ExpiredCardError` |
| `401198` | `ParallelLoanError` |
| `401664` | `UserMissingFieldError` |
| `40166404` | `InvalidFieldError` |
| `401689` | `BarcodeNotFoundError` |
| `401690` | `IllegalBarcodeError` |
| `401822` | `CannotRenewError` |
| `401823` | `LoanNotFoundError` |
| `401861` | `UserNotFoundError` |
| `401873` | `RequestFailedError` |
| `401876` | `POUpdateFailedError` |
| `402203` | `MMSIdNotFoundError` |
| `402504` | `ScanItemRetrievalError` |

## Rate limiting

`ThresholdError` (HTTP 429) means Alma's rate limit was hit. almapy retries it
automatically and cuts its own request rate in response, so you should rarely
see one escape. If you do, the institution's quota is being consumed faster than
almapy alone can account for – most likely another application sharing the same
key or institution.

`ThrottleTimeoutError` is different: it is raised locally, without a request
being sent, when `max_wait` is configured and elapses while waiting for a token.
It subclasses `TimeoutError` as well as `AlmapyError`.

See [Rate limiting](rate-limiting.md).

## Full reference

Every exception class is listed in the [API reference](../api/exceptions.md).
