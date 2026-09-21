# Bibs, holdings and items

Reached as `client.bibs`, which carries the record, holding and item methods
plus sub-namespaces for loans, requests and digital representations.

Most methods here want the full MMS ID / holding ID / item PID path.
[`get_item`][almapy._bibs.AlmaClientBibNS.get_item] resolves all three from a
barcode, which is usually where to start:

```python
item = await client.bibs.get_item("39001234567890")
mms_id = item.bib_data.mms_id
holding_id = item.holding_data.holding_id
item_pid = item.item_data.pid
```

!!! warning "Not everything returns a `Box`"

    The holding and bib-record methods – `get_holding`, `update_holding`,
    `create_holding`, `get_bib`, `create_bib`, `update_bib` – exchange raw MARC
    XML as `str`, because Alma has no JSON representation of a MARC record.
    Those methods take no `model=` argument. See [Responses](../guide/responses.md).

## `client.bibs`

::: almapy._bibs.AlmaClientBibNS

## `client.bibs.loans`

::: almapy._bibs.AlmaClientBibLoansNS

## `client.bibs.requests`

::: almapy._bibs.AlmaClientBibRequestsNS

## `client.bibs.representations`

Alma Digital representations on a record, and the files under each one. Files are
not uploaded through this API – `create_file` registers a file already staged in
the institution's S3 upload folder.

::: almapy._representations.AlmaClientBibRepresentationsNS
