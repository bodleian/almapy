# Responses

## Box by default

Most methods return JSON wrapped in a [Box](https://github.com/cdgriffith/Box),
which makes Ex Libris' rather XMLish JSON less verbose to work with —
`resp.bib_data.title` rather than `resp["bib_data"]["title"]`.

```python
item = await client.bibs.get_item("39001234567890")

print(item.bib_data.title)
print(item.item_data.barcode)
print(item.holding_data.holding_id)
```

A `Box` is still a `dict` underneath, so subscripting, `.get()`, `in` and
iteration all work as usual. Dot access is a convenience, not a replacement:

```python
title = item.bib_data.get("title", "[no title]")
if "item_data" in item:
    ...
```

Alma's `{value, desc}` pairs come through as you would expect —
`item.item_data.base_status.value` and `.desc`.

## The seven raw XML methods

Seven methods return the raw response body as a `str`, because they deal in MARC
XML records that would be mangled by a round-trip through JSON:

| Method | Returns |
|--------|---------|
| `bibs.get_bib`, `bibs.create_bib`, `bibs.update_bib` | MARC XML record |
| `bibs.get_holding`, `bibs.create_holding`, `bibs.update_holding` | MARC XML holding |
| `analytics.get_raw_report` | Analytics report XML |

These take no `model=` argument — there is no `Box` to validate. Parse them with
your own MARC or XML library.

Everything else, letters included, returns a `Box`.

## Typing responses with `model=`

`Box` is a pragmatic default, not the only option. Every Box-returning method
accepts an optional `model=` keyword argument. When supplied, the raw `Box` is
passed to `model.model_validate()` and the validated instance is returned
instead.

```python
from pydantic import BaseModel

from almapy import AlmaClient


class User(BaseModel):
    """A partial model — Alma returns far more than this.

    Pydantic ignores unknown fields by default, so you only need to declare the
    ones you actually use.
    """

    primary_id: str
    first_name: str | None = None
    last_name: str | None = None


async def main() -> None:
    async with AlmaClient(apikey="KEY") as client:
        # Returns User instead of Box
        user = await client.users.get_user("jsmith", model=User)
        print(user.last_name)

        # Default behaviour unchanged — still returns Box
        raw = await client.users.get_user("jsmith")
        print(raw.last_name)
```

almapy adds no modelling dependency of its own. Any class with a
`model_validate` classmethod works — pydantic, or something hand-rolled.

The overloads are written so the return type follows the argument: pass `model=`
and mypy sees your model type, omit it and mypy sees `Box`. You do not need to
annotate or cast.

## Request bodies

Write methods take a plain `dict`, or any object exposing either
`model_dump(mode="json")` or `dump(mode="json")`. `model_dump` is pydantic v2's
own API, so a `BaseModel` works directly — no shim needed, and still no pydantic
dependency on almapy's side. Both checks are `runtime_checkable` Protocols, so
they are purely structural — nothing needs to import from almapy or inherit from
it:

```python
class UserUpdate(BaseModel):
    first_name: str


async def main() -> None:
    async with AlmaClient(apikey="KEY") as client:
        await client.users.update_user("jsmith", {"first_name": "Jane"})
        await client.users.update_user("jsmith", UserUpdate(first_name="Jane"))
```

almapy serialises once, before the retry loop, and sends the result as the JSON
body. If an object exposes both methods `dump` wins, on the grounds that a model
carrying a custom `dump` is expressing a deliberate wire shape that should not
be bypassed.

This applies to JSON writes only. The MARC XML methods take a `str`.

!!! warning "Writes replace the whole record"

    Alma's update endpoints are not patches. `update_user`, `update_item`,
    `update_po_line` and friends replace the entire object with the body you
    send, so a partial body silently drops every field it omits — including
    roles, addresses and notes.

    Fetch, modify, send back:

    ```python
    user = await client.users.get_user("jsmith")
    user.contact_info.email[0].email_address = "new@example.ac.uk"
    await client.users.update_user("jsmith", user)
    ```

    A `Box` round-trips straight back into a write method, which is what makes
    this read-modify-write pattern comfortable.

## Pagination

List endpoints return a page plus a `total_record_count` for the whole result
set. Page with `limit` and `offset`:

```python
offset, members = 0, []
while True:
    page = await client.config.sets.get_members("1234567890", limit=100, offset=offset)
    members.extend(page.member)
    offset += 100
    if offset >= int(page.total_record_count):
        break
```

Defaults for `limit` are not uniform — most methods default to 100, but
`get_users`, `get_requests`, `get_items` and `get_portfolios` default to 10.
Check the [API reference](../api/client.md) for the method you are calling.

[`analytics.get_full_report`][almapy._analytics.AlmaClientAnalyticsNS.get_full_report]
is the exception: it follows Alma's resumption token itself and returns every
row.
