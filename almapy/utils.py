import json
import re
import xml

import httpx
import xmltodict
from glom import Coalesce, glom


class ArgError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.message = "Invalid Argument: " + msg


class APIClientError(Exception):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(msg)
        self.message = f"API Error {code}: {msg}"


class APIServerError(APIClientError):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        self.message = f"Server Error {code}: {msg}"


class ThresholdError(APIServerError):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        self.message = f"API Threshold Error {code}: {msg}"


class BarcodeNotFoundError(APIClientError):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        self.barcode = msg.split(" ")[-1][0:-1]
        self.message = f"Barcode not found: {self.barcode}"


def handle_http_error(response: httpx.Response) -> None:
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
    elif 600 > response.status_code > 500:
        raise APIServerError(code, message)
    else:
        raise APIClientError(code, message)
