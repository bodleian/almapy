import json
import logging
import operator
import re
import traceback
import xml
from collections import OrderedDict
from collections.abc import Callable
from http import HTTPStatus
from typing import (
    Any,
    Protocol,
    TypedDict,
    TypeVar,
    cast,
    runtime_checkable,
)

import niquests
import xmltodict
from box import Box
from glom import Coalesce, GlomError, glom

from almapy import exceptions
from almapy._logging import request_id

_error_log = logging.getLogger("almapy.error")

RESP_TYPE = Box

_ModelT = TypeVar("_ModelT")


@runtime_checkable
class Dumpable(Protocol):
    """Structural type for objects that serialize to a JSON-safe dict.

    Satisfied by any object exposing ``dump(mode: str) -> dict[str, Any]`` —
    notably alma_models' base model class — without requiring an import or
    inheritance relationship in either direction.
    """

    def dump(self, mode: str = ...) -> dict[str, Any]: ...


Body = dict[str, Any] | Dumpable


class Request(TypedDict, total=False):
    request_type: str
    description: str
    manual_description: str
    holding_id: str
    pickup_location_type: str
    pickup_location_library: str
    pickup_location_circulation_desk: str
    target_destination: dict[str, str]
    material_type: dict[str, str]
    last_interest_date: dict[str, str]
    partial_digitization: bool
    chapter_or_article_title: str
    volume: str
    issue: str
    part: str
    date_of_publication: str
    chapter_or_article_author: str
    required_pages_range: dict[str, str]
    full_chapter: str
    comment: str
    request_status: str
    copyrights_declaration_signed_by_patron: bool


def _parse_xml(text: str) -> "OrderedDict[str, Any]":
    try:
        body = xmltodict.parse(text)
    except xml.parsers.expat.ExpatError:  # type: ignore  # noqa: PGH003
        text = re.sub(r"https://(.*)&(.*)", r"\g<1>&#38;\g<2>", text)
        body = xmltodict.parse(text)
    return cast("OrderedDict[str, Any]", body)


def _validate_response(response: niquests.Response) -> None:
    """Raise an appropriate exception if the response indicates an error."""
    assert response.status_code is not None
    if response.status_code >= HTTPStatus.BAD_REQUEST:
        _raise_for_error_body(response)


_RETRYABLE = (
    exceptions.ThresholdError,  # 429 rate limit
    exceptions.APIServerError,  # 5xx server errors
    niquests.ConnectionError,
    niquests.Timeout,  # base for ReadTimeout, ConnectTimeout
    niquests.exceptions.ChunkedEncodingError,  # server drops connection mid-response
)


def _is_urllib3_transport_assertion(exc: BaseException) -> bool:
    """Treat urllib3-future async transport assertions as transient request failures."""
    if not isinstance(exc, AssertionError):
        return False

    return any("urllib3" in frame.filename for frame in traceback.extract_tb(exc.__traceback__))


def _is_urllib3_http1_reuse_race(exc: BaseException) -> bool:
    """Treat known urllib3-future HTTP/1.1 async pool races as transient transport failures."""
    frames = traceback.extract_tb(exc.__traceback__)
    from_urllib3 = any("urllib3" in frame.filename for frame in frames)
    if not from_urllib3:
        return False

    if isinstance(exc, RuntimeError):
        return str(exc) == (
            "Cannot generate a new stream ID because the connection is not idle. "
            "HTTP/1.1 is not multiplexed and we do not support HTTP pipelining."
        )

    if isinstance(exc, ValueError):
        return str(exc).endswith("is not in deque") and "AsyncPendingSignal(" in str(exc)

    return False


def _should_retry(exc: BaseException) -> bool:
    """Return True if the exception is a transient transport or server failure.

    This is the *backpressure* predicate: it decides whether a failure should
    depress the adaptive rate limit. It is deliberately method-agnostic — a 429
    or 5xx is a signal about Alma's health regardless of which verb provoked it.
    Use :func:`_retry_predicate` to decide whether to actually replay a request.
    """
    return (
        isinstance(exc, _RETRYABLE)
        or _is_urllib3_transport_assertion(exc)
        or _is_urllib3_http1_reuse_race(exc)
    )


# Repetition of these is safe by RFC 9110 semantics: replaying one cannot create
# a second record, so the full transient set is retryable.
_IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "PUT", "DELETE"})

# Failures that prove Alma never processed the request. A 429 is a gateway
# rejection, and a connect timeout means no connection was ever established, so
# neither can leave a half-applied write behind. These stay retryable for POST.
_UNPROCESSED_RETRYABLE = (
    exceptions.ThresholdError,
    niquests.ConnectTimeout,
)


def _retry_predicate(method: str, *, retry: bool | None = None) -> Callable[[BaseException], bool]:
    """Build the stamina retry predicate for a single request.

    A read timeout or 5xx on a POST usually means Alma *did* process the write
    and the response was lost, so replaying it creates a duplicate loan, request
    or PO line. Non-idempotent verbs are therefore only retried on failures that
    prove the request never landed.

    Args:
        method: HTTP verb for the request.
        retry: ``True`` forces full retries even for a write, ``False`` disables
            retries entirely, ``None`` (default) picks by method idempotency.
    """
    if retry is False:
        return lambda _exc: False
    if retry is True or method.upper() in _IDEMPOTENT_METHODS:
        return _should_retry
    return lambda exc: isinstance(exc, _UNPROCESSED_RETRYABLE)


def _get_error_class(
    status_code: int,
) -> "type[exceptions.APIServerError | exceptions.APIClientError] | None":
    if status_code == HTTPStatus.TOO_MANY_REQUESTS:
        return exceptions.ThresholdError
    if status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return exceptions.APIServerError
    if status_code >= HTTPStatus.BAD_REQUEST:
        return exceptions.APIClientError
    return None


_ERROR_MAPPING: dict[str, type[exceptions.APIServerError | exceptions.APIClientError]] = {
    "401689": exceptions.BarcodeNotFoundError,
    "401161": exceptions.LoanLimitError,
    "401201": exceptions.LoanBlockedError,
    "401873": exceptions.RequestFailedError,
    "40166404": exceptions.InvalidFieldError,
    "401163": exceptions.LoanBlockedError,
    "401198": exceptions.ParallelLoanError,
    "402504": exceptions.ScanItemRetrievalError,
    "401129": exceptions.NoItemsCanFulfillRequestError,
    "401136": exceptions.ParallelRequestError,
    "401876": exceptions.POUpdateFailedError,
    "402203": exceptions.MMSIdNotFoundError,
    "401861": exceptions.UserNotFoundError,
    "401823": exceptions.LoanNotFoundError,
    "401168": exceptions.ExpiredCardError,
    "400042": exceptions.ItemAlreadyLoanedToUserError,
    "401690": exceptions.IllegalBarcodeError,
    "401153": exceptions.CannotBeLoanedError,
    "401151": exceptions.UserIsNotAPatronError,
}


def _raise_for_error_body(response: niquests.Response) -> None:
    """Parse an error response body and raise the appropriate exception. Always raises."""
    assert response.status_code is not None
    assert response.text is not None
    ct = response.headers.get("Content-Type")
    if ct and "xml" in ct:
        body = _parse_xml(response.text)
    elif ct == "text/plain":
        _error_log.warning(
            "API error %s: %s",
            response.status_code,
            response.text,
            extra={"req_id": request_id.get(), "status_code": response.status_code},
        )
        raise exceptions.APIServerError(str(response.status_code), response.text)
    else:
        body = json.loads(response.text)

    try:
        code, message = glom(
            body,
            (
                Coalesce(
                    "web_service_result.errorList.error.0",
                    "errorList.error.0",
                    "web_service_result.errorList.error",
                ),
                operator.itemgetter("errorCode", "errorMessage"),
            ),
        )
    except GlomError as e:
        _error_log.warning(
            "API error %s: Unknown error (unparseable body)",
            response.status_code,
            extra={"req_id": request_id.get(), "status_code": response.status_code},
        )
        raise exceptions.APIServerError(str(response.status_code), "Unknown error") from e

    message = code if not message else message.strip()

    error_class = _ERROR_MAPPING.get(str(code)) or _get_error_class(response.status_code)
    _error_log.warning(
        "API error %s: [%s] %s",
        response.status_code,
        code,
        message,
        extra={
            "req_id": request_id.get(),
            "status_code": response.status_code,
            "alma_code": str(code),
        },
    )
    raise error_class(code, message)  # type: ignore[misc]
