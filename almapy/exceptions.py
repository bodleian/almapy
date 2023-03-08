class ArgError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.message = "Invalid Argument: " + msg


class APIClientError(Exception):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(msg)
        self.code = code
        self.error = msg
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


class LoanLimitError(APIClientError):
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(code, msg)
