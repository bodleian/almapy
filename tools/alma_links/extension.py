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
    """Append a ``See Also`` link to every method with a known Alma endpoint."""

    def on_function(self, *, func: griffe.Function, **_: Any) -> None:
        """Add the link to this function's docstring, if it has an endpoint."""
        entry = _MAPPING.get(func.canonical_path)
        if entry is None or func.docstring is None:
            return
        # Appended to the raw docstring rather than inserted as a parsed section:
        # griffe parses lazily, so the Google parser picks this up as a real
        # "See Also" section and renders it beside Parameters and Returns.
        func.docstring.value += f"\n\nSee Also:\n    [Alma: {entry['summary']}]({entry['url']})\n"
