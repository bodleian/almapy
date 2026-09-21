# Exceptions

Every exception almapy raises descends from `AlmapyError`, so a single
`except AlmapyError` catches anything originating in the library.

## The hierarchy

The classes below are rendered in source order, each showing its immediate base,
which makes the overall shape hard to see. In full:

```text
Exception
└── AlmapyError                          catch-all for anything almapy raises
    ├── _AlmaError                       internal; carries Alma's code and message
    │   ├── APIServerError               5xx, already retried before you see it
    │   │   └── MalformedResponseError   2xx whose body was not the promised format
    │   └── APIClientError               4xx, your request – not retried
    │       ├── ThresholdError           429, rate limit exceeded
    │       ├── BarcodeNotFoundError
    │       ├── BibNotInCollectionError
    │       ├── CannotBeLoanedError
    │       ├── CannotRenewError
    │       ├── ExpiredCardError
    │       ├── IllegalBarcodeError
    │       ├── InvalidCodeError
    │       ├── InvalidFieldError
    │       ├── ItemAlreadyLoanedToUserError
    │       ├── LoanBlockedError
    │       ├── LoanLimitError
    │       ├── LoanNotFoundError
    │       ├── MMSIdNotFoundError
    │       ├── NoItemsCanFulfillRequestError
    │       ├── POUpdateFailedError
    │       ├── ParallelLoanError
    │       ├── ParallelRequestError
    │       ├── RequestFailedError
    │       ├── ScanItemRetrievalError
    │       ├── UserIsNotAPatronError
    │       ├── UserMissingFieldError
    │       └── UserNotFoundError
    └── ThrottleTimeoutError             also a TimeoutError; raised locally,
                                         without a request being sent
```

Two things the per-class listing does not make obvious:

`_AlmaError` appears as the base of most classes but has no entry below, being
private. It exists to hold Alma's numeric `code` and `message`; catch
`APIClientError` or `APIServerError` instead, which is the distinction that
actually matters.

`ThrottleTimeoutError` sits outside that branch entirely. It is raised by
almapy's own rate limiter before any request goes out, so it carries no Alma
error code, and it subclasses `TimeoutError` as well – `except TimeoutError`
catches it too.

See [Errors](../guide/errors.md) for which of these to expect in practice and
how Alma's numeric codes map onto them.

## Reference

::: almapy.exceptions
    options:
      show_root_heading: false
      members_order: source
