# Analytics

Reached as `client.analytics`.

!!! warning "Analytics does not return `Box` objects"

    Alma returns Analytics results as XML rather than JSON, paginated with a
    resumption token. This is the one namespace that returns XML text or plain
    dictionaries, and its methods take no `model=` argument.

    Use [`get_full_report`][almapy._analytics.AlmaClientAnalyticsNS.get_full_report]
    for parsed rows – it follows the resumption token for you – or
    [`get_raw_report`][almapy._analytics.AlmaClientAnalyticsNS.get_raw_report]
    for the untouched XML.

!!! note "Report size costs requests"

    `get_full_report` issues one API request per `limit` rows, all of which count
    against the institution's daily quota. Raise `limit` (Alma caps it at 1000)
    to reduce the number of round trips.

::: almapy._analytics.AlmaClientAnalyticsNS
