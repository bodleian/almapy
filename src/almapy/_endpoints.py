"""Alma API endpoint definitions."""

import re
from collections.abc import Mapping
from enum import StrEnum
from urllib.parse import quote

_SLASH_BEARING = frozenset({"PO_LINE_ID"})
"""Path parameters whose Alma identifier space contains slashes.

Migrated PO line numbers are `<order>/<line>` – `204029292/0005` is line 0005 of
order 204029292 – and Alma addresses the record at a path with that slash left
raw: its own search results give the record's `link` as
`/acq/po-lines/204029292/0005`. Encoded to `%2F`, the Ex Libris gateway refuses
the request at the connector, before Alma sees it, with a bare Tomcat page
carrying no error code – indistinguishable from an outage, and unreachable.

Every other parameter keeps the strict encoding. A slash arriving in a free-text
barcode or "other ID" is the route-confusion bug this encoding exists to stop.
"""


def _encode(name: str, value: str) -> str:
    """Percent-encode one path parameter so it cannot act as URL syntax.

    The slash is the single exception, and only for `_SLASH_BEARING`, where it
    separates the parts of one of Alma's own identifiers. Each segment either
    side of it is still encoded strictly, so nothing else gets through that way,
    and a segment that would rewrite the path – empty, `.` or `..` – is refused
    rather than sent: letting the slash through is only safe while it stays a
    separator and cannot become navigation.
    """
    text = str(value)
    if name not in _SLASH_BEARING:
        return quote(text, safe="")
    segments = text.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        msg = f"{name}: {text!r} has an empty or relative path segment"
        raise ValueError(msg)
    return "/".join(quote(segment, safe="") for segment in segments)


class AlmaEndpoint(StrEnum):
    USERS = "/users"
    USER = "/users/{USER_ID}"
    USER_LOANS = "/users/{USER_ID}/loans"
    USER_LOAN = "/users/{USER_ID}/loans/{LOAN_ID}"
    USER_FEES = "/users/{USER_ID}/fees"
    USER_FEES_ALL = "/users/{USER_ID}/fees/all"
    USER_FEE = "/users/{USER_ID}/fees/{FEE_ID}"
    USER_REQUESTS = "/users/{USER_ID}/requests"
    USER_REQUEST = "/users/{USER_ID}/requests/{REQUEST_ID}"
    USER_ATTACHMENTS = "/users/{USER_ID}/attachments"

    BARCODE = "/items"
    ITEM = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items/{ITEM_PID}"
    ITEMS = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items"
    PORTFOLIOS = "/bibs/{MMS_ID}/portfolios"
    HOLDING = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}"
    HOLDINGS = "/bibs/{MMS_ID}/holdings"
    ITEM_LOANS = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items/{ITEM_PID}/loans"
    ITEM_LOAN = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items/{ITEM_PID}/loans/{LOAN_ID}"
    BIBS = "/bibs"
    BIB = "/bibs/{MMS_ID}"
    BIB_LOANS = "/bibs/{MMS_ID}/loans"
    BIB_LOAN = "/bibs/{MMS_ID}/loans/{LOAN_ID}"
    BIB_REQUESTS = "/bibs/{MMS_ID}/requests"
    BIB_REQUEST = "/bibs/{MMS_ID}/requests/{REQUEST_ID}"
    ITEM_REQUESTS = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items/{ITEM_PID}/requests"
    ITEM_REQUEST = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items/{ITEM_PID}/requests/{REQUEST_ID}"
    REPRESENTATIONS = "/bibs/{MMS_ID}/representations"
    REPRESENTATION = "/bibs/{MMS_ID}/representations/{REP_ID}"
    REPRESENTATION_FILES = "/bibs/{MMS_ID}/representations/{REP_ID}/files"
    REPRESENTATION_FILE = "/bibs/{MMS_ID}/representations/{REP_ID}/files/{FILE_ID}"

    PO_LINE = "/acq/po-lines/{PO_LINE_ID}"
    PO_LINE_ITEM = "/acq/po-lines/{PO_LINE_ID}/items/{ITEM_PID}"

    SETS = "/conf/sets"
    SET = "/conf/sets/{SET_ID}"
    SET_MEMBERS = "/conf/sets/{SET_ID}/members"
    LIBRARIES = "/conf/libraries"
    LOCATIONS = "/conf/libraries/{LIBRARY_CODE}/locations"
    LOCATION = "/conf/libraries/{LIBRARY_CODE}/locations/{LOCATION_CODE}"
    CIRC_DESKS = "/conf/libraries/{LIBRARY_CODE}/circ-desks"
    DEPARTMENTS = "/conf/departments"
    LETTERS = "/conf/letters"
    LETTER = "/conf/letters/{LETTER_ID}"
    JOBS = "/conf/jobs"
    JOB = "/conf/jobs/{JOB_ID}"
    JOB_INSTANCES = "/conf/jobs/{JOB_ID}/instances"
    JOB_INSTANCE = "/conf/jobs/{JOB_ID}/instances/{INSTANCE_ID}"
    JOB_INSTANCE_MATCHES = "/conf/jobs/{JOB_ID}/instances/{INSTANCE_ID}/matches"
    CODE_TABLES = "/conf/code-tables"
    CODE_TABLE = "/conf/code-tables/{TABLE_CODE}"
    INTEGRATION_PROFILES = "/conf/integration-profiles"
    INTEGRATION_PROFILE = "/conf/integration-profiles/{PROFILE_ID}"

    REPORTS = "/analytics/reports"

    def build(self, path: Mapping[str, str] | None = None) -> str:
        """Substitute path parameters. Raises ValueError on missing or extra keys."""
        if path is None:
            path = {}
        expected = set(re.findall(r"\{(\w+)\}", self.value))
        provided = set(path.keys())
        if missing := expected - provided:
            msg = f"{self.name}: missing path params {missing}"
            raise ValueError(msg)
        if extra := provided - expected:
            msg = f"{self.name}: unexpected path params {extra}"
            raise ValueError(msg)
        # Encode so nothing survives as a URL delimiter – see `_encode`. Alma
        # "other IDs", card numbers and barcodes are free text arriving from
        # upstream systems: unencoded, "smith#1" fetched user "smith" because the
        # fragment never left the client, "a/b" hit a different route, and
        # "x?apikey=y" became a query string.
        return self.value.format_map({k: _encode(k, v) for k, v in path.items()})
