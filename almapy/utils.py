import json
import re
import xml

import httpx
import xmltodict


class ArgError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.message = "Invalid Argument: " + msg


class APIError(Exception):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(msg)
        self.message = f"API Error {code}: {msg}"


class ThresholdError(APIError):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        self.message = f"API Threshold Error {code}: {msg}"


class TempAPIError(APIError):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        self.message = f"Server Error {code}: {msg}"


class BarcodeNotFoundError(APIError):
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
        error = body["web_service_result"]["errorList"]["error"]
        code = error["errorCode"]
        message = error["errorMessage"]
    else:
        body = json.loads(response.text)
        # There are two different error formats, depending on the API endpoint. Why? Who knows.
        if "web_service_result" in body:
            error = body["web_service_result"]["errorList"]["error"]
        else:
            error = body["errorList"]["error"][0]
        code = error["errorCode"]
        message = error["errorMessage"]
        if message == '':
            message = code

    if response.status_code == 429:
        raise ThresholdError(code, message)
    if code == "401689":
        raise BarcodeNotFoundError(code, message)
    elif 600 > response.status_code > 500:
        raise TempAPIError(code, message)
    else:
        raise APIError(code, message)
