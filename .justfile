default: lint test

lint:
    uv run ruff format
    uv run ruff check --fix
    uv run mypy .
    uv run deptry .

upgrade:
    uv lock --upgrade
    uv sync

# Serve the docs at localhost:8000 with live reload
docs:
    uv run zensical serve

# Build the docs into site/, as CI does. --strict turns griffe's warnings about
# malformed docstrings, and unresolvable ::: identifiers, into build failures.
docs-build:
    uv run zensical build --clean --strict

lint-ci:
    uv run ruff format --check
    uv run ruff check --no-fix
    uv run mypy .
    uv run deptry .

test *args:
    uv run --no-sync pytest {{ args }}

# Run the tests with coverage, failing under the configured floor
test-cov *args:
    uv run --no-sync pytest --cov=almapy --cov-report=term-missing {{ args }}

# Run the test suite on every supported Python version
test-all *args:
    #!/usr/bin/env bash
    set -euo pipefail
    # Keep this list in step with requires-python and the Python classifiers in
    # pyproject.toml. Each version gets its own environment because `just test`
    # uses --no-sync, which reuses whatever environment it finds rather than
    # building one for the requested version.
    failed=()
    for v in 3.11 3.12 3.13 3.14; do
        echo "===== Python $v ====="
        env_dir=".venv-$v"
        UV_PROJECT_ENVIRONMENT="$env_dir" uv sync --all-groups --python "$v" --quiet
        if ! UV_PROJECT_ENVIRONMENT="$env_dir" uv run --no-sync pytest {{ args }}; then
            failed+=("$v")
        fi
    done
    if [ ${#failed[@]} -gt 0 ]; then
        echo "FAILED on: ${failed[*]}" >&2
        exit 1
    fi
    echo "test-all: passed on 3.11 3.12 3.13 3.14"

# Import the built wheel from a clean venv (run after build-check)
smoke:
    #!/usr/bin/env bash
    set -euo pipefail
    # The test suite imports almapy from src/ via the editable install, so a
    # file missing from the wheel — py.typed, or a whole module — passes every
    # test and only breaks for whoever pip installs it.
    wheel=$(ls dist/*.whl 2>/dev/null | head -1)
    if [ -z "$wheel" ]; then
        echo "no wheel in dist/ — run 'just build-check' first" >&2
        exit 1
    fi
    tmp=$(mktemp -d)
    trap 'rm -rf "$tmp"' EXIT
    uv venv "$tmp/venv" --quiet
    uv pip install --python "$tmp/venv/bin/python" --quiet "$wheel"
    "$tmp/venv/bin/python" - <<'PY'
    import pathlib

    import almapy
    from almapy import AlmaClient, AlmapyError, ThrottleTimeoutError  # public API

    location = pathlib.Path(almapy.__file__)
    assert "site-packages" in location.parts, f"not the installed wheel: {location}"

    # Constructing the client imports every namespace module, so a module left
    # out of the wheel fails here rather than at a user's first call.
    client = AlmaClient("smoke-test-key")
    for ns in ("users", "bibs", "acq", "config", "analytics", "primo"):
        assert hasattr(client, ns), f"namespace missing from the wheel: {ns}"

    assert (location.parent / "py.typed").is_file(), (
        "py.typed missing — downstream mypy would silently ignore all of almapy's types"
    )

    print(f"smoke: imports clean from {location.parent}")
    PY
    echo "smoke: wheel installs and imports correctly"

publish: build-check
    uv publish --username __token__

# Build the artifacts, failing if secrets or patron data are in them
build-check:
    #!/usr/bin/env bash
    set -euo pipefail
    # An explicit sdist `include` bypasses VCS-ignore, so anything untracked but
    # present in the working tree gets packed. This is the last line of defence
    # before a credential reaches a package registry.
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