"""Griffe extension linking each namespace method to its Ex Libris documentation.

The links are a property of the rendered site, not of the source: each URL is
about 120 characters of base64, and putting 85 of them in docstrings would add a
lot of noise for no benefit to anyone reading the code.

The mapping in ``endpoints.json`` is generated and validated by ``generate.py``
(``just docs-links``); this only reads it, so a docs build needs no network access.
"""

import json
from pathlib import Path
from typing import Any

import griffe

_MAPPING: dict[str, dict[str, str]] = json.loads(
    (Path(__file__).parent / "endpoints.json").read_text()
)


class AlmaDocLinks(griffe.Extension):
    """Attach each method's Alma endpoint documentation to the griffe object."""

    def on_function(self, *, func: griffe.Function, **_: Any) -> None:
        """Record the endpoint link, if this method has one."""
        entry = _MAPPING.get(func.canonical_path)
        if entry is None:
            return
        # Stashed on the object rather than appended to the docstring, because
        # docstring content renders below the heading and the link belongs beside
        # it. templates/python/material/function.html.jinja reads this back and
        # renders it in the `labels` block, next to the `async` chip.
        func.extra["alma_links"] = entry
