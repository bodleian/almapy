from typing import NoReturn

import json
import re
import xml

import httpx
import xmltodict
from glom import Coalesce, glom

from almapy.exceptions import APIClientError, APIServerError, BarcodeNotFoundError, LoanLimitError, ThresholdError


def handle_http_error(response: httpx.Response) -> NoReturn:
    # Sometimes the server ignores us and returns XML instead of JSON. Fun.
    if "application/xml" in response.headers.get("Content-Type"):
        text = response.text
        # HTTP 503 ROUTING_ERROR may contain malformed XML as it does not escape &, which is not XML-legal. We catch
        # and fix this below.
        try:
            body = xmltodict.parse(text)
        except xml.parsers.expat.ExpatError:
            text = re.sub(r"https://(.*)&(.*)", r"\g<1>&#38;\g<2>", text)
            body = xmltodict.parse(text)
    else:
        body = json.loads(response.text)
    # Some errors omit the web_service_result level in the JSON response. Why? Who knows.
    code, message = glom(
        body,
        (
            Coalesce("web_service_result.errorList.error.0", "errorList.error.0", "web_service_result.errorList.error"),
            lambda x: (x["errorCode"], x["errorMessage"]),
        ),
    )
    if message == "":
        message = code

    if response.status_code == 429:
        raise ThresholdError(code, message)
    if code == "401689":
        raise BarcodeNotFoundError(code, message)
    if code == "401161":
        raise LoanLimitError(code, message)
    elif 600 > response.status_code > 500:
        raise APIServerError(code, message)
    else:
        raise APIClientError(code, message)
