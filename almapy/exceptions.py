import re


class ArgError(Exception):
    def __init__(self, msg: str) -> None:
        self.message = "Invalid Argument: " + msg
        super().__init__(self.message)


class APIClientError(Exception):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(msg)
        self.code = code
        self.error = msg
        self.message = f"API Error {code}: {msg}"


class APIServerError(Exception):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(msg)
        self.code = code
        self.error = msg
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


class LoanLimitError(APIClientError):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)


class LoanBlockedError(APIClientError):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        m = re.match(r"(?P<type>.*?) {2}- {3}(?P<description>.*?)\. (?P<note>.*) Scope: (?P<scope>.*)", msg)
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
    def __init__(self, code: str, msg: str) -> None:
        m = re.match(r"Given field (?P<field_name>\w+) has invalid value (?P<field_value>\w+),.*", msg)
        if m:
            self.field_name = m.group("field_name")
            self.field_value = m.group("field_value")
            super().__init__(code, f"Invalid field value '{self.field_value}' for field '{self.field_name}'")
        else:
            self.field_name = ""
            self.field_value = ""
            super().__init__(code, msg)


class RequestFailedError(APIClientError):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
        self.message = msg
