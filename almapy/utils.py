from typing import Dict, NoReturn, TypedDict

import json
import re
import xml

import httpx
import xmltodict
from glom import Coalesce, GlomError, glom

from almapy.exceptions import (
    APIClientError,
    APIServerError,
    BarcodeNotFoundError,
    InvalidFieldError,
    LoanBlockedError,
    LoanLimitError,
    ParallelLoanError,
    RequestFailedError,
    ThresholdError,
)


class Request(TypedDict):
    request_type: str
    description: str
    manual_description: str
    holding_id: str
    pickup_location_type: str
    pickup_location_library: str
    pickup_location_circulation_desk: str
    target_destination: Dict[str, str]
    material_type: Dict[str, str]
    last_interest_date: Dict[str, str]
    partial_digitization: bool
    chapter_or_article_title: str
    volume: str
    issue: str
    part: str
    date_of_publication: str
    chapter_or_article_author: str
    required_pages_range: Dict[str, str]
    full_chapter: str
    comment: str
    request_status: str
    copyrights_declaration_signed_by_patron: bool


def parse_xml(text: str):
    try:
        body = xmltodict.parse(text)
    except xml.parsers.expat.ExpatError:
        text = re.sub(r"https://(.*)&(.*)", r"\g<1>&#38;\g<2>", text)
        body = xmltodict.parse(text)
    return body


def handle_http_error(response: httpx.Response) -> NoReturn:
    # Server errors are often returned as XML, even if we asked for JSON. Fun.
    if "xml" in response.headers.get("Content-Type"):
        # HTTP 503 ROUTING_ERROR may contain malformed XML as it does not escape &, which is not XML-legal. We catch
        # and fix this below.
        body = parse_xml(response.text)
    else:
        body = json.loads(response.text)

    # Some errors omit the web_service_result level in the JSON response. Why? Who knows.
    try:
        code, message = glom(
            body,
            (
                Coalesce(
                    "web_service_result.errorList.error.0", "errorList.error.0", "web_service_result.errorList.error"
                ),
                lambda x: (x["errorCode"], x["errorMessage"]),
            ),
        )
    except GlomError as e:
        print(response.text)
        if response.status_code > 499:
            raise APIServerError(str(response.status_code), "Unknown error") from e
        else:
            raise APIClientError(str(response.status_code), "Unknown error") from e

    if message == "":
        message = code
    else:
        message: str = message.strip()

    if response.status_code == 429:
        raise ThresholdError(code, message)
    elif code == "401689":
        raise BarcodeNotFoundError(code, message)
    elif code == "401161":
        raise LoanLimitError(code, message)
    elif code == "401201":
        raise LoanBlockedError(code, message)
    elif code == "401873":
        raise RequestFailedError(code, message)
    elif code == "40166404":
        raise InvalidFieldError(code, message)
    elif code == "401163":
        raise LoanBlockedError(code, message)
    elif code == "401198":
        raise ParallelLoanError(code, message)
    elif 600 > response.status_code > 500:
        raise APIServerError(code, message)
    else:
        raise APIClientError(code, message)
