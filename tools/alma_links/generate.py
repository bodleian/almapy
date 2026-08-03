"""Generate the mapping from almapy methods to their Ex Libris documentation.

Ex Libris doc URLs are deterministic::

    https://developers.exlibrisgroup.com/alma/apis/docs/<area>/<base64("VERB /almaws/v1/<path>")>/

They cannot be derived from almapy's own endpoint paths, though, because Alma's
placeholder naming is inconsistent -- ``{user_id}`` but ``{libraryCode}`` and
``{codeTableName}``, a bare ``{id}`` for integration profiles, and ``{item_pid}``
becoming ``{item_id}`` on the item-loans endpoint. Guessing gets about 70 of 85.

So the paths come from Alma's own published OpenAPI specs instead. almapy's
endpoints are matched against them with placeholders normalised away, and the URL
is built from the spec's spelling.

Run with ``just docs-links`` to regenerate, or ``just docs-links-check`` to
re-validate what is already committed. Both need network access; neither runs as
part of a docs build.
"""

import argparse
import ast
import base64
import json
import re
import sys
import urllib.request
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "almapy"
MAPPING_PATH = Path(__file__).parent / "endpoints.json"

SPEC_URL = "https://developers.exlibrisgroup.com/wp-content/uploads/alma/openapi/{area}.json"
DOC_URL = "https://developers.exlibrisgroup.com/alma/apis/docs/{area}/{token}/"
AREAS = ("users", "bibs", "acq", "conf", "analytics")

# The docs site is a single-page app: it answers 200 for any path and echoes the
# requested path back into the page, so neither the status code nor the path
# appearing in the body proves an endpoint exists. Only the server-rendered
# endpoint documentation does, and this heading is part of it.
MARKER = "API Description"

# BaseNamespace helper -> HTTP verb.
VERB_BY_HELPER = {
    "_get": "GET",
    "_get_text": "GET",
    "_post": "POST",
    "_post_text": "POST",
    "_put": "PUT",
    "_put_text": "PUT",
    "_delete": "DELETE",
}

# Endpoints absent from every OpenAPI spec. A wrong link is worse than no link, so
# anything without a hand-verified URL is reported and skipped rather than guessed.
OVERRIDES: dict[str, tuple[str, str]] = {
    # GET /items is a shortcut for retrieving an item by barcode rather than by its
    # full path, so it has no spec entry of its own. Alma documents it on the page
    # for the endpoint it abbreviates, which get_item_by_pid also points at.
    "almapy._bibs.AlmaClientBibNS.get_item": (
        "https://developers.exlibrisgroup.com/alma/apis/docs/bibs/"
        "R0VUIC9hbG1hd3MvdjEvYmlicy97bW1zX2lkfS9ob2xkaW5ncy97aG9sZGluZ19pZH0vaXRlbXMve2l0ZW1fcGlkfQ==/",
        "Retrieve Item and label printing information",
    ),
}

_PLACEHOLDER = re.compile(r"\{[^}]+\}")


@dataclass(frozen=True)
class Method:
    """A public namespace method and the endpoint it calls."""

    qualname: str
    verb: str
    path: str


def _endpoint_paths() -> dict[str, str]:
    """Map ``AlmaEndpoint`` member names to their URL paths."""
    tree = ast.parse((SRC / "_endpoints.py").read_text())
    paths: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "AlmaEndpoint":
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Constant):
                    target = stmt.targets[0]
                    if isinstance(target, ast.Name):
                        paths[target.id] = str(stmt.value.value)
    return paths


def _is_overload(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        getattr(dec, "id", getattr(dec, "attr", "")) == "overload" for dec in fn.decorator_list
    )


def _called_endpoints(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> Iterator[tuple[str, str]]:
    """Yield (verb, AlmaEndpoint member) for each request the method issues."""
    for node in ast.walk(fn):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            continue
        verb = VERB_BY_HELPER.get(node.func.attr)
        if verb is None:
            continue
        for arg in node.args:
            if isinstance(arg, ast.Attribute) and getattr(arg.value, "id", None) == "AlmaEndpoint":
                yield verb, arg.attr


def discover_methods() -> list[Method]:
    """Find every public namespace method and the endpoint it calls."""
    paths = _endpoint_paths()
    found: list[Method] = []
    for module in sorted(SRC.glob("_*.py")):
        tree = ast.parse(module.read_text())
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            for fn in cls.body:
                if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                    continue
                if fn.name.startswith("_") or _is_overload(fn):
                    continue
                for verb, member in _called_endpoints(fn):
                    qualname = f"almapy.{module.stem}.{cls.name}.{fn.name}"
                    found.append(Method(qualname, verb, paths[member]))
    return found


def _fetch(url: str) -> str:
    if not url.startswith("https://developers.exlibrisgroup.com/"):  # pragma: no cover
        msg = f"refusing to fetch off-site URL: {url}"
        raise ValueError(msg)
    # ruff: ignore[suspicious-url-open-usage] - the host is checked immediately above
    with urllib.request.urlopen(url, timeout=60) as resp:
        raw: bytes = resp.read()
    return raw.decode("utf-8", "ignore")


def _normalise(path: str) -> str:
    """Strip placeholder *names* so almapy's spelling can match Alma's."""
    return _PLACEHOLDER.sub("{}", path.rstrip("/"))


def load_spec_index() -> dict[tuple[str, str], tuple[str, str, str]]:
    """Index every documented operation by (verb, normalised path)."""
    index: dict[tuple[str, str], tuple[str, str, str]] = {}
    for area in AREAS:
        spec: dict[str, Any] = json.loads(_fetch(SPEC_URL.format(area=area)))
        for path, operations in spec["paths"].items():
            for verb, operation in operations.items():
                if verb.lower() not in {"get", "post", "put", "delete"}:
                    continue
                key = (verb.upper(), _normalise(path.replace("/almaws/v1", "")))
                summary = str(operation.get("summary") or "").strip()
                index[key] = (area, path, summary)
    return index


def doc_url(area: str, verb: str, spec_path: str) -> str:
    token = base64.b64encode(f"{verb} {spec_path}".encode()).decode()
    return DOC_URL.format(area=area, token=token)


def validate(url: str) -> bool:
    """True if the URL is a real endpoint page rather than the app's shell."""
    try:
        return MARKER in _fetch(url)
    except OSError:
        return False


def build() -> tuple[dict[str, dict[str, str]], list[Method]]:
    """Return the mapping, plus the methods no documentation could be found for."""
    index = load_spec_index()
    mapping: dict[str, dict[str, str]] = {}
    skipped: list[Method] = []
    for method in discover_methods():
        if override := OVERRIDES.get(method.qualname):
            url, summary = override
            mapping[method.qualname] = {"url": url, "summary": summary}
            continue
        entry = index.get((method.verb, _normalise(method.path)))
        if entry is None:
            skipped.append(method)
            continue
        area, spec_path, summary = entry
        mapping[method.qualname] = {
            "url": doc_url(area, method.verb, spec_path),
            "summary": summary or f"{method.verb} {method.path}",
        }
    return dict(sorted(mapping.items())), skipped


def check(mapping: dict[str, dict[str, str]]) -> list[str]:
    """Return the qualnames whose URLs no longer resolve to a real page."""
    names = list(mapping)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = pool.map(validate, (mapping[n]["url"] for n in names))
    return [name for name, ok in zip(names, results, strict=True) if not ok]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the committed mapping without rewriting it",
    )
    args = parser.parse_args(argv)

    if args.check:
        if not MAPPING_PATH.exists():
            print(f"no mapping at {MAPPING_PATH} - run without --check first")
            return 1
        mapping = json.loads(MAPPING_PATH.read_text())
        broken = check(mapping)
        print(f"checked {len(mapping)} links, {len(broken)} broken")
        for name in broken:
            print(f"  BROKEN {name}\n         {mapping[name]['url']}")
        return 1 if broken else 0

    mapping, skipped = build()
    print(f"matched {len(mapping)} methods against the OpenAPI specs")
    for method in skipped:
        print(
            f"  SKIPPED {method.qualname}\n          no spec entry for {method.verb} {method.path}"
        )

    broken = check(mapping)
    if broken:
        print(f"\n{len(broken)} generated links did not resolve - not writing:")
        for name in broken:
            print(f"  {name}\n    {mapping[name]['url']}")
        return 1

    MAPPING_PATH.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n")
    print(f"\nvalidated all {len(mapping)} links, wrote {MAPPING_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
