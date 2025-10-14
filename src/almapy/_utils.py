from __future__ import annotations

import json
import operator
import re
import xml
from collections import OrderedDict
from http import HTTPStatus
from typing import (
    TYPE_CHECKING,
    Any,
    TypedDict,
    cast,
)

import xmltodict
from box import Box
from glom import Coalesce, GlomError, glom
from gracy import GracefulValidator

from almapy import exceptions

if TYPE_CHECKING:
    import httpx

RESP_TYPE = Box


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


def _parse_xml(text: str) -> OrderedDict[str, Any]:
    try:
        body = xmltodict.parse(text)
    except xml.parsers.expat.ExpatError:  # type: ignore  # noqa: PGH003
        text = re.sub(r"https://(.*)&(.*)", r"\g<1>&#38;\g<2>", text)
        body = xmltodict.parse(text)
    return cast("OrderedDict[str, Any]", body)


class AlmaErrorValidator(GracefulValidator):
    def check(self, response: httpx.Response) -> None:
        if response.status_code >= HTTPStatus.BAD_REQUEST:
            _handle_error(response)


def _get_error_class(
    status_code: int,
) -> type[exceptions.APIServerError | exceptions.APIClientError] | None:
    if status_code == HTTPStatus.TOO_MANY_REQUESTS:
        return exceptions.ThresholdError
    if status_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
        return exceptions.APIServerError
    if status_code >= HTTPStatus.BAD_REQUEST:
        return exceptions.APIClientError
    return None


def process_response(response: httpx.Response) -> tuple[str, str] | None:
    if response.status_code == HTTPStatus.OK:
        return None

    ct = response.headers.get("Content-Type")
    if ct and "xml" in ct:
        body = _parse_xml(response.text)
    elif response.headers.get("Content-Type") == "text/plain":
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
        raise exceptions.APIServerError(str(response.status_code), "Unknown error") from e

    message = code if not message else message.strip()

    return code, message


def _handle_error(response: httpx.Response) -> None:
    if processed := process_response(response):
        code, message = processed
    else:
        return

    error_mapping: dict[
        HTTPStatus | str, type[exceptions.APIServerError | exceptions.APIClientError]
    ] = {
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

    error_class = error_mapping.get(str(code)) or _get_error_class(response.status_code)

    if error_class:
        raise error_class(code, message)

    raise exceptions.APIClientError(code, message)
