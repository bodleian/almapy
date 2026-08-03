"""Shared helpers: error mapping, retry predicates and request-body protocols.

Internal to the library, but two pieces of it shape the public API:

- ``Body`` – the type accepted by every write method. A plain ``dict``, or any
  object satisfying the ``Dumpable`` or ``ModelDumpable`` protocols, which is how a
  Pydantic model can be passed as a request body without a conversion shim.
- ``_raise_for_error_body`` – maps Alma's numeric error codes onto the specific
  exception classes in ``almapy.exceptions``. Adding support for a new Alma error
  code means adding a class there and an entry in ``_ERROR_MAPPING`` here.
"""

import json
import logging
import operator
import re
import traceback
import xml
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

    Satisfied by any object exposing ``dump(*, mode: str) -> dict[str, Any]`` –
    notably alma_models' base model class – without requiring an import or
    inheritance relationship in either direction.

    ``mode`` is keyword-only to match how :func:`_dump_body` calls it. A method
    taking it positionally-or-by-keyword still satisfies this, so the
    keyword-only form accepts strictly more implementations.
    """

    def dump(self, *, mode: str = ...) -> dict[str, Any]: ...


@runtime_checkable
class ModelDumpable(Protocol):
    """Structural type for pydantic-style models.

    ``model_dump`` is pydantic v2's own API, so a plain ``BaseModel`` can be
    passed as a request body without a ``dump`` shim. Kept separate from
    :class:`Dumpable` because a Protocol cannot express "either method".

    ``mode`` must be keyword-only: pydantic declares it after ``*``, and a
    protocol asking for it positionally is not satisfied by a keyword-only
    implementation – which silently made every ``BaseModel`` fail to match here
    under a type checker, despite working at runtime.
    """

    def model_dump(self, *, mode: str = ...) -> dict[str, Any]: ...


Body = dict[str, Any] | Dumpable | ModelDumpable


def _dump_body(body: Any) -> Any:
    """Convert a model-like request body to a JSON-safe dict.

    ``dump`` wins over ``model_dump`` when an object has both – a pydantic model
    carrying a custom ``dump`` is expressing a deliberate wire shape, and that
    should not be silently bypassed. Anything else (a plain dict, a Box) is
    returned untouched.
    """
    if isinstance(body, Dumpable):
        return body.dump(mode="json")
    if isinstance(body, ModelDumpable):
        return body.model_dump(mode="json")
    return body


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


def _parse_xml(text: str) -> dict[str, Any]:
    try:
        body = xmltodict.parse(text)
    except xml.parsers.expat.ExpatError:  # type: ignore  # ruff: ignore[blanket-type-ignore]
        text = re.sub(r"https://(.*)&(.*)", r"\g<1>&#38;\g<2>", text)
        body = xmltodict.parse(text)
    return cast(dict[str, Any], body)


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
    depress the adaptive rate limit. It is deliberately method-agnostic – a 429
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

    When a POST fails on a read timeout or a 5xx, the client cannot tell whether
    Alma applied the write before the response was lost, so replaying it risks a
    duplicate loan, request or PO line. Non-idempotent verbs are therefore only
    retried on failures that prove the request never landed.

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


def _error_class_for(
    status_code: int,
) -> type[exceptions.APIServerError | exceptions.APIClientError]:
    """Status-appropriate exception class, never None.

    _raise_for_error_body only runs for >= 400, so _get_error_class always
    matches; the fallback keeps mypy happy and fails safe.
    """
    return _get_error_class(status_code) or exceptions.APIServerError


def _body_excerpt(text: str, limit: int = 500) -> str:
    """A short, loggable stand-in for an unparseable body."""
    return text.strip()[:limit] or "<empty body>"


def _raise_for_error_body(response: niquests.Response) -> None:
    """Parse an error response body and raise the appropriate exception. Always raises."""
    assert response.status_code is not None
    assert response.text is not None
    status = response.status_code
    ct = response.headers.get("Content-Type") or ""

    body: Any
    if "xml" in ct:
        body = _parse_xml(response.text)
    else:
        try:
            body = json.loads(response.text)
        except ValueError as e:
            # Not every error body is Alma's JSON: a proxy returns an HTML 502,
            # an overloaded gateway an empty 503, and Alma itself sends
            # "text/plain;charset=UTF-8" – which an exact-equality check on the
            # Content-Type never matched. Letting json.loads raise here escaped
            # as a bare JSONDecodeError rather than an AlmapyError, so the
            # status code was lost, _should_retry returned False and
            # record_failure never fired: precisely the transient failures
            # retries and backpressure exist for.
            detail = _body_excerpt(response.text)
            _error_log.warning(
                "API error %s: unparseable body: %s",
                status,
                detail,
                extra={"req_id": request_id.get(), "status_code": status},
            )
            raise _error_class_for(status)(str(status), detail) from e

    try:
        code, message = glom(
            body,
            (
                Coalesce(
                    "web_service_result.errorList.error.0",
                    "errorList.error.0",
                    "web_service_result.errorList.error",
                    # Alma sometimes sends a bare object rather than a list.
                    "errorList.error",
                ),
                operator.itemgetter("errorCode", "errorMessage"),
            ),
        )
    except GlomError as e:
        # Status-appropriate, not hardcoded APIServerError: a 404 whose body
        # does not match the Coalesce chain is still a client error, and
        # APIServerError is retryable – so it cost three round-trips and
        # needlessly depressed the adaptive rate limit.
        detail = _body_excerpt(response.text)
        _error_log.warning(
            "API error %s: unrecognised error body: %s",
            status,
            detail,
            extra={"req_id": request_id.get(), "status_code": status},
        )
        raise _error_class_for(status)(str(status), detail) from e

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
