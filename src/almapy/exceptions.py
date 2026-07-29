"""More specific exceptions for Alma API errors, used in response to (non-HTTP) error codes."""

import re


class AlmapyError(Exception):
    """Root exception for all exceptions raised by almapy.

    Catch this to handle any error originating from the library.
    """


class _AlmaError(AlmapyError):
    """Shared base for all Alma API exceptions raised by the error handler.

    Two tiers of exceptions exist:
    - Handler-raised: constructed with (code, msg) by _raise_for_error_body in _utils.py.
    - Namespace-enriched: constructed with bespoke signatures by namespace methods that
      catch a handler-raised exception, extract domain context (e.g. loan_id), and re-raise
      with a richer type (e.g. CannotRenewError, UserMissingFieldError, InvalidCodeError).
    """

    def __init__(self, code: str, msg: str) -> None:
        # args must mirror this signature: Exception.__reduce__ pickles as
        # cls(*self.args). Passing the formatted string gave args a single
        # element, so unpickling every almapy exception raised TypeError —
        # behind a ProcessPoolExecutor or Celery worker the real Alma error was
        # replaced by that TypeError at the deserialisation boundary.
        super().__init__(code, msg)
        self.code = code
        self.error = msg
        self.message = f"{msg} [{code}]"

    def __str__(self) -> str:
        # Defined once here rather than per subclass: with two-element args the
        # default would render the tuple, and subclasses that set self.message
        # would otherwise disagree with str(self).
        return self.message


class APIClientError(_AlmaError):
    """Base exception for generic client-caused errors (HTTP 400s)."""


class APIServerError(_AlmaError):
    """Base exception for generic server-related errors (HTTP 500s)."""


class ThresholdError(APIClientError):
    """Raised when the API rate limit is exceeded."""

    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        self.message = f"API Threshold Error {code}: {msg}"


class BarcodeNotFoundError(APIClientError):
    """Raised when the specified barcode was not found on Alma.

    Attributes:
        barcode (str): The barcode that was not found.
    """

    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        # Alma ends the message with the bare barcode and a full stop:
        # "No items found for barcode 1234567890." The old [-1][1:-1] slice took
        # a character off each end, so it dropped the barcode's first character
        # as well as the full stop. Other endpoints bracket or quote the value,
        # hence stripping punctuation rather than a fixed number of characters.
        # msg == code means errorMessage was empty and _raise_for_error_body
        # substituted the code.
        tokens = msg.split()
        self.barcode = tokens[-1].strip("[]()'\".,;:") if tokens and msg != code else ""
        self.message = f"Barcode not found: {self.barcode}" if self.barcode else msg


class MMSIdNotFoundError(APIClientError):
    """Raised when the specified MMS ID was not found on Alma.

    Attributes:
        mms (str): The MMS ID that was not found.
    """

    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        # The old msg.split(" ")[3] raised IndexError on any shorter message —
        # from inside the error handler, destroying the API error it described.
        # Matching the ID is independent of the surrounding wording.
        m = re.search(r"\b(?P<mms>\d{8,})\b", msg)
        self.mms = m.group("mms") if m else ""
        self.message = f"MMS ID not found: {self.mms}" if self.mms else msg


class LoanLimitError(APIClientError):
    """Raised when an item could not be loaned due to a limit on number of simultaneous loans."""


class LoanBlockedError(APIClientError):
    """Raised when an item could not be loaned due to a block on the user.

    Attributes:
        type (str): The block type.
        description (str): The block description.
        note (str): The block note.
        scope (str): The block scope.
    """

    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        m = re.match(
            r"(?P<type>.*?) {2}- {3}(?P<description>.*?)\. (?P<note>.*) Scope: (?P<scope>.*)",
            msg,
        )
        if m:
            self.type = m.group("type")
            self.description = m.group("description")
            self.note = m.group("note")
            self.scope = m.group("scope")
        else:
            self.type = ""
            self.description = ""
            self.note = ""
            self.scope = ""


class InvalidFieldError(APIClientError):
    """Raised when the user object contained invalid fields, often roles.

    Attributes:
        field_name (str): The name of the invalid field.
        field_value (str): The invalid value.
    """

    def __init__(self, code: str, msg: str) -> None:
        m = re.match(
            r"Given field (?P<field_name>\w+) has invalid value (?P<field_value>\w+),.*",
            msg,
        )
        if m:
            self.field_name = m.group("field_name")
            self.field_value = m.group("field_value")
            super().__init__(
                code,
                f"Invalid field value '{self.field_value}' for field '{self.field_name}'",
            )
        else:
            self.field_name = ""
            self.field_value = ""
            super().__init__(code, msg)


class RequestFailedError(APIClientError):
    """Generic exception for when request creation failed."""


class ParallelLoanError(APIClientError):
    """Raised when an item was unable to be loaned because they have a loan on another copy."""


class ParallelRequestError(APIClientError):
    """Raised when an item could not be requested because they have a request on another copy."""


class UserMissingFieldError(APIClientError):
    """Some fields in the user object are mandatory and Alma throws an error if they are absent.

    Attributes:
        user_id (str): The primary ID of the user.
    """

    def __init__(self, msg: str, user_id: str) -> None:
        super().__init__("401664", msg)
        self.args = (msg, user_id)  # mirror this signature so pickling round-trips
        self.user_id = user_id
        self.message = msg


class CannotRenewError(APIClientError):
    """Unable to renew a loan for whatever reason.

    Raised in place of the generic client error when Alma returns code 401822 —
    the item is requested by someone else, the renewal limit is reached, or a
    block applies. Alma's own reason is in ``error``.

    Attributes:
        loan_id: The loan that could not be renewed.
    """

    def __init__(self, msg: str, loan_id: str) -> None:
        super().__init__("401822", msg)
        self.args = (msg, loan_id)  # mirror this signature so pickling round-trips
        self.loan_id = loan_id
        self.message = msg


class UserNotFoundError(APIClientError):
    """No user with the provided identifier exists on Alma.

    Attributes:
        user_id (str): The primary ID of the user.
    """

    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        m = re.match(
            r"User with identifier (?P<identifier>[A-Za-z0-9._-]+) was not found.",
            msg,
        )
        if m:
            self.user_id = m.group("identifier")
        else:
            self.user_id = ""
        self.message = msg

    def __str__(self) -> str:
        return self.message


class InvalidCodeError(APIClientError):
    """For when an invalid code is specified when updating an item."""

    def __init__(self, msg: str) -> None:
        super().__init__("401873", msg)
        self.args = (msg,)  # mirror this signature so pickling round-trips
        self.message = msg


class ScanItemRetrievalError(APIClientError):
    """Raised by scan in endpoint when the scan succeeds but item info is not returned [?]."""


class NoItemsCanFulfillRequestError(APIClientError):
    """Raised when creating a request that no items can fulfill."""


class POUpdateFailedError(APIClientError):
    """Raised when a PO could not be updated for any reason."""

    def __init__(self, code: str, msg: str) -> None:
        msg = msg.replace("Failed to update the PO Line. Error:", "").strip()
        super().__init__(code, msg)
        self.message = msg


class LoanNotFoundError(APIClientError):
    """Raised when a loan could not be found."""

    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        m = re.match(
            r"Loan ID (?P<identifier>[0-9]+) does not exist\.",
            msg,
        )
        if m:
            self.loan_id = m.group("identifier")
        else:
            self.loan_id = ""
        self.message = msg

    def __str__(self) -> str:
        return self.message


class ExpiredCardError(APIClientError):
    """Raised when creating a loan for a card that has expired."""


class ItemAlreadyLoanedToUserError(APIClientError):
    """Raised when trying to create a loan for an item that is already loaned to the user."""


class IllegalBarcodeError(APIClientError):
    """Raised when trying to retrieve an item with an illegal barcode."""


class CannotBeLoanedError(APIClientError):
    """Raised when an item cannot be loaned from the circulation desk."""


class UserIsNotAPatronError(APIClientError):
    """Raised when a user cannot borrow because they either don't have a patron role or it has expired."""


class ThrottleTimeoutError(TimeoutError, AlmapyError):
    """Raised when max_wait is exceeded waiting for adaptive throttle."""
