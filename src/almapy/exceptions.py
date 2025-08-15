"""More specific exceptions for Alma API errors, used in response to (non-HTTP) error codes."""

import re


class APIClientError(Exception):
    """Base exception for generic client-caused errors (HTTP 400s)."""

    def __init__(self, code: str, msg: str) -> None:
        super().__init__(f"{msg} [{code}]")
        self.code = code
        self.error = msg
        self.message = f"{msg} [{code}]"


class APIServerError(Exception):
    """Base exception for generic server-related errors (HTTP 500s)."""

    def __init__(self, code: str, msg: str) -> None:
        super().__init__(f"{msg} [{code}]")
        self.code = code
        self.error = msg
        self.message = f"{msg} [{code}]"


class ThresholdError(APIServerError):
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
        self.barcode = msg.split(" ")[-1][0:-1]
        self.message = f"Barcode not found: {self.barcode}"


class MMSIdNotFoundError(APIClientError):
    """Raised when the specified MMS ID was not found on Alma.

    Attributes:
        mms (str): The MMS ID that was not found.
    """

    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        self.mms = msg.split(" ")[3]
        self.message = f"MMS ID not found: {self.mms}"


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
        self.user_id = user_id
        self.message = msg


class CannotRenewError(APIClientError):
    """Unable to renew a loan for whatever reason.

    Attributes:
        loan_id (str)
    """

    def __init__(self, msg: str, loan_id: str) -> None:
        super().__init__("401822", msg)
        self.loan_id = loan_id
        self.message = msg

    def __str__(self) -> str:
        return self.message


class UserNotFoundError(APIClientError):
    """No user with the provided identifier exists on Alma.

    Attributes:
        user_id (str): The primary ID of the user.
    """

    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        m = re.match(
            r"User with identifier (?P<identifier>[A-Za-z0-9]+) was not found.",
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
        self.message = msg

    def __str__(self) -> str:
        return self.message


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
