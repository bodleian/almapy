set shell := ["bash", "-c"]

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

publish:
    rm -r -fo dist
    uv build
    uv publish --username __token__

hook:
    uv run pre-commit install

unhook:
    uv run pre-commit uninstall