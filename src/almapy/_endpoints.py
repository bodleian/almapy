"""Alma API endpoint definitions."""

import re
from collections.abc import Mapping
from enum import StrEnum


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
    ITEM_REQUESTS = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items/{ITEM_PID}/requests"
    ITEM_REQUEST = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items/{ITEM_PID}/requests/{REQUEST_ID}"

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
        return self.value.format_map(path)
