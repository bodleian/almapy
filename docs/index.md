# almapy

Async Python wrapper for the [Ex Libris Alma API](https://developers.exlibrisgroup.com/alma/apis/).

almapy wraps Alma's REST API with the parts you would otherwise write yourself:
rate limiting that adapts to backpressure, retries that know not to replay a
write, Alma's numeric error codes mapped onto real exception classes, and
responses you can reach into with dot notation.

```python
import asyncio
from almapy import AlmaClient


async def main() -> None:
    async with AlmaClient("your-api-key") as client:
        item = await client.bibs.get_item("39001234567890")
        print(item.bib_data.title)

        loans = await client.users.loans.get_loans("12345678")
        for loan in loans.item_loan:
            print(loan.title, loan.due_date)


asyncio.run(main())
```

## Install

```bash
uv add almapy
# or
pip install almapy
```

Requires Python 3.11 or newer. The package ships type information (`py.typed`),
so mypy and your editor see the full API.

## Where to go next

<div class="grid cards" markdown>

- **[Getting started](guide/getting-started.md)** – API keys, choosing a region,
  and your first request.
- **[Responses](guide/responses.md)** – `Box` dot-notation access, the raw MARC
  XML methods, and typing responses with Pydantic models.
- **[Errors](guide/errors.md)** – the exception hierarchy and how Alma's error
  codes map onto it.
- **[Rate limiting](guide/rate-limiting.md)** – the token bucket, adaptive
  backpressure, and why writes are not retried.
- **[Logging](guide/logging.md)** – the four loggers, correlation IDs, and
  structlog.
- **[API reference](api/client.md)** – every namespace and method.

</div>

## The namespace tree

Everything hangs off the client as an attribute path that reads like the thing
you are asking for:

```
client.users            users, and their loans, fines and requests
client.bibs             records, holdings, items, and their loans and requests
client.acq              purchase order lines and receiving
client.config           sets, libraries, letters, jobs, code tables
client.analytics        Alma Analytics reports
client.primo            Primo search
```

## Licence

MIT. Developed at the [Bodleian Libraries](https://www.bodleian.ox.ac.uk/),
University of Oxford.
