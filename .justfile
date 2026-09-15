default: lint test

lint:
    uv run ruff format
    uv run ruff check --fix
    uv run mypy .
    uv run deptry .

upgrade:
    uv lock --upgrade
    uv sync

# Regenerate the Alma endpoint links from Ex Libris' OpenAPI specs (needs network)
docs-links:
    uv run python tools/alma_links/generate.py

# Re-validate the committed links without rewriting them (needs network).
# Deliberately not in CI: it depends on an external site, and would block
# unrelated PRs whenever developers.exlibrisgroup.com is slow or restructured.
docs-links-check:
    uv run python tools/alma_links/generate.py --check

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
    # file missing from the wheel – py.typed, or a whole module – passes every
    # test and only breaks for whoever pip installs it.
    wheel=$(ls dist/*.whl 2>/dev/null | head -1)
    if [ -z "$wheel" ]; then
        echo "no wheel in dist/ – run 'just build-check' first" >&2
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
        "py.typed missing – downstream mypy would silently ignore all of almapy's types"
    )

    print(f"smoke: imports clean from {location.parent}")
    PY
    echo "smoke: wheel installs and imports correctly"

# Bump version, changelog and tag from the conventional commits since the last
# release. Needs jj-cz >= 0.4.0: it promotes the [Unreleased] block into the new
# section, so write the entries there in the feature commit. Review CHANGELOG.md
# afterwards, then `just release`.
bump:
    jj-cz bump
    just changelog-check "$(uv version --short)"

# Push the bump, wait for CI to pass on it, then push the tag and create the
# GitHub Release with notes from CHANGELOG.md. @- must be the bump commit, as
# `just bump` leaves it.
release:
    #!/usr/bin/env bash
    set -euo pipefail
    version="$(uv version --short)"
    just changelog-check "$version"
    bump_change="$(jj log -r @- --no-graph -T change_id)"
    tag_change="$(jj log -r "tags(exact:\"$version\")" --no-graph -T change_id)"
    if [ "$bump_change" != "$tag_change" ]; then
        echo "tag $version is not on the bump commit (@-) – run 'just bump' first" >&2
        exit 1
    fi
    # Editing the changelog after the bump rewrites the commit and leaves the
    # tag on the hidden predecessor, so re-point it before pushing.
    jj tag set "$version" -r @- --allow-move
    jj bookmark set main -r @-
    jj git push --bookmark main
    # The tag and the release are what cannot be taken back – a version can
    # never be reused – so neither is created until the ci workflow is green
    # on the pushed commit. release.yml runs the same checks again before
    # publishing, but by then the tag and release already exist.
    sha="$(jj log -r @- --no-graph -T commit_id)"
    run_id=""
    for _ in $(seq 1 24); do
        run_id="$(gh run list --workflow ci.yml --commit "$sha" --json databaseId --jq '.[0].databaseId // empty')"
        [ -n "$run_id" ] && break
        sleep 5
    done
    if [ -z "$run_id" ]; then
        echo "no ci run appeared for $sha within two minutes" >&2
        exit 1
    fi
    echo "waiting for ci run $run_id on $sha"
    gh run watch "$run_id" --exit-status
    jj git push --tag "$version"
    just changelog-section "$version" \
        | gh release create "$version" --verify-tag --title "$version" --notes-file -

# Fail unless CHANGELOG.md has a section for VERSION and nothing left under [Unreleased]
changelog-check version:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! grep -q '^## \[{{ version }}\]' CHANGELOG.md; then
        echo "CHANGELOG.md has no section for {{ version }}" >&2
        exit 1
    fi
    if awk '/^## \[Unreleased\]/ {p = 1; next} /^## \[/ {p = 0} p && NF {found = 1} END {exit !found}' CHANGELOG.md; then
        echo "CHANGELOG.md still has entries under [Unreleased] – release them or move them" >&2
        exit 1
    fi

# Print the CHANGELOG.md section for VERSION without its heading (the release notes)
changelog-section version:
    @awk -v v='{{ version }}' \
        '/^## \[/ {h = "## [" v "]"; p = (substr($0, 1, length(h)) == h); next} \
         p {lines[n++] = $0} \
         END {while (n > 0 && lines[n - 1] ~ /^[[:space:]]*$/) n--; \
              s = 0; while (s < n && lines[s] ~ /^[[:space:]]*$/) s++; \
              for (i = s; i < n; i++) print lines[i]}' CHANGELOG.md

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
        echo "REFUSING TO PUBLISH – secrets or patron data in build artifacts:" >&2
        echo "$leaked" >&2
        exit 1
    fi
    echo "build-check: no secrets found in dist/"

hook:
    uv run pre-commit install

unhook:
    uv run pre-commit uninstall