default: lint test

lint:
    uv run ruff format
    uv run ruff check --fix
    uv run mypy .
    uv run deptry .

upgrade:
    uv lock --upgrade
    uv sync

lint-ci:
    uv run ruff format --check
    uv run ruff check --no-fix
    uv run djlint .
    uv run mypy .

test *args:
    uv run --no-sync pytest {{ args }}

publish: build-check
    uv publish --username __token__

# Build, then refuse to go further if secrets or patron data made it into the
# artifacts. An explicit sdist `include` bypasses VCS-ignore, so this is the
# last line of defence before a key reaches a package registry.
build-check:
    #!/usr/bin/env bash
    set -euo pipefail
    rm -rf dist
    uv build
    leaked=$(for f in dist/*.tar.gz dist/*.whl; do
        case "$f" in
            *.whl) unzip -Z1 "$f" ;;
            *) tar tzf "$f" ;;
        esac
    done | grep -Ei '(^|/)\.?env$|\.env\.|(^|/)barcodes\.txt$|\.pem$|\.p12$|(^|/)secrets?\.' || true)
    if [ -n "$leaked" ]; then
        echo "REFUSING TO PUBLISH — secrets or patron data in build artifacts:" >&2
        echo "$leaked" >&2
        exit 1
    fi
    echo "build-check: no secrets found in dist/"

hook:
    uv run pre-commit install

unhook:
    uv run pre-commit uninstall