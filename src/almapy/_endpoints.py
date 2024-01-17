from __future__ import annotations

from gracy import BaseEndpoint


class AlmaEndpoint(BaseEndpoint):
    USERS = "/users"
    USER = "/users/{USER_ID}"
    USER_LOANS = "/users/{USER_ID}/loans"
    USER_LOAN = "/users/{USER_ID}/loans/{LOAN_ID}"
    USER_FEES = "/users/{USER_ID}/fees"
    USER_REQUESTS = "/users/{USER_ID}/requests"
    USER_REQUEST = "/users/{USER_ID}/requests/{REQUEST_ID}"

    BARCODE = "/items"
    ITEM = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items/{ITEM_PID}"
    ITEMS = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items"
    PORTFOLIOS = "/bibs/{MMS_ID}/portfolios"
    HOLDING = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}"
    HOLDINGS = "/bibs/{MMS_ID}/holdings"
    ITEM_LOANS = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items/{ITEM_PID}/loans"
    ITEM_LOAN = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items/{ITEM_PID}/loans/{LOAN_ID}"
    BIB = "/bibs/{MMS_ID}"
    BIB_LOANS = "/bibs/{MMS_ID}/loans"
    BIB_LOAN = "/bibs/{MMS_ID}/loans/{LOAN_ID]"
    ITEM_REQUESTS = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items/{ITEM_PID}/requests"
    ITEM_REQUEST = "/bibs/{MMS_ID}/holdings/{HOLDING_ID}/items/{ITEM_PID}/requests/{REQUEST_ID}"

    PO_LINE = "/acq/po-lines/{PO_LINE_ID}"

    SETS = "/conf/sets"
    SET = "/conf/sets/{SET_ID}"
    SET_MEMBERS = "/conf/sets/{SET_ID}/members"
    LIBRARIES = "/conf/libraries"
    LOCATIONS = "/conf/libraries/{LIBRARY_CODE}/locations"
    LOCATION = "/conf/libraries/{LIBRARY_CODE}/locations/{LOCATION_CODE}"
    CIRC_DESKS = "/conf/libraries/{LIBRARY_CODE}/circ-desks"
    LETTERS = "/conf/letters"
    LETTER = "/conf/letters/{LETTER_ID}"

    REPORTS = "/analytics/reports"
