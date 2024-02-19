# almapy

[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linting: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Introduction
This is a wrapper library for the Alma API. The design goal is to smooth off some of the rough edges of the APIs to make them easier to use.

The library is async, using httpx under the hood.

Notable QoL:
- Takes care of rate-limiting.
- Retries server errors (including rate limit errors) automatically.
- Handles some weird edge cases like incorrect response types.
- Adds more informative exceptions than just HTTP status codes, based on Ex Libris' own error codes.

Convenient methods, namespaced by functional area, are available for a lot of common endpoints, but these are not comprehensive and are added as needed. Said methods don't try to do anything fancy with parameters or responses as of yet.

All methods return JSON in the form of a [Box](https://github.com/cdgriffith/Box), except where XML clearly makes more sense (holdings, letters). Box is used to make Ex Libris' rather XMLish JSON less verbose to work with. In the longer term the hope is to have specific classes for every response type, and this is underway in a separate project, but it will take a long time.

## Quickstart
```bash
poetry add  "git+https://gitlab.bodleian.ox.ac.uk/bodl3011/almapy.git"
```


```python
import asyncio
from almapy import AlmaClient
from almapy.exceptions import APIClientError, APIServerError

BARCODES = ["98279242", "24569754", "345782365"]

async def fetch_item(client: AlmaClient, barcode: str):
    resp = await client.bibs.get_item(barcode)
    return resp

async def main():
    client = AlmaClient(apikey="KEY", rate_limit=10)
    tasks = [fetch_item(client, barcode) for barcode in BARCODES]

    # Option One
    results = asyncio.gather(*tasks)  # Can use return_exceptions=True to include exceptions in the list instead of interrupting
    for result in results:
        print(result.bib_data.title)

    # Option Two
    for result in asyncio.as_completed(tasks):
        try:
            resp = await result
            print(resp.bib_data.title)
        except APIServerError as e:
            print(f"Server error: {e}")
        except APIClientError as e:
            print(f"Client error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

```

## TODO
- [ ] Better documentation
- [ ] More endpoints
- [ ] Specific response types
- [ ] Logging
