# Copilot Instructions

## Project Overview

Subsea combines two concerns in one repository:
  - a Python package scaffold (`src/subsea`, `pyproject.toml`) for subsea
    data/ML work;
  - an ALM/configuration hub (`.github/`, `docs/`, `configs/`, `scripts/`) with
    workflow and governance assets.

## Build, Test, and Lint Commands

Use `uv` for Python environment and task execution (`requires-python = ">=3.13"`
in `pyproject.toml`).

```bash
# install dependencies
uv sync
uv sync --extra dev

# run tests (full suite)
uv run pytest

# run a single test (node-id form)
uv run pytest path/to/test_file.py::test_name

# run tests by expression
uv run pytest -k "pattern"

# lint Python package code
uv run pylint src/subsea
```

CI workflows in `.github/workflows/` enforce documentation and workflow hygiene:

```bash
# mirrors CI markdown lint scope
markdownlint-cli2 "**/*.md"

# CI uses yamllint over repository files
yamllint .
```

## High-Level Architecture

- `SUBSEA.md` and `ARCHICTERURE.md` define the domain model: **Subsea
  namespace** containing **Projects**, which are governed by **Resources**,
  **Policies**, and **Configurations**.
- `.github/workflows/` applies repository governance: markdown/yaml linting
  (`ci-lint.yml`), PR title linting (`pr-title-lint.yml`), and secret scanning
  (`security-gitleaks.yml`).
- `src/subsea/` is currently a minimal package surface, while `notebooks/` holds
  executable Marimo notebooks and `scripts/` contains project/bootstrap and
  Git-signing helpers.

## Key Conventions

### Python formatting baseline

`src/subsea/__init__.py` sets the expected Python header/modeline pattern:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:
```

Follow 2-space indentation in Python files in this repository.

### Notebook format

Notebooks are Marimo Python files (`notebooks/*.py`), not `.ipynb` sources.

```bash
uv run marimo run notebooks/notebook.py
uv run marimo edit notebooks/notebook.py
```

### Commit and PR conventions

- Commit guidance exists in both `CONTRIBUTING.md` (type/scope/subject format)
  and `commit-template.txt` (ticket-prefixed template). Follow the format
  expected by the target project workflow and keep commits signed
  (`scripts/git-commit-signing-ssh.sh` helps configure SSH signing).
- PR titles are validated by `amannn/action-semantic-pull-request` in
  `.github/workflows/pr-title-lint.yml`; keep titles semantic and
  machine-parseable.

### Security scanning expectation

`security-gitleaks.yml` runs Gitleaks on PRs and pushes to `main`; avoid
introducing credentials or private keys in tracked files.

## Reusable Copilot Prompts

Prompt templates live in `.github/prompts/`:
- `review-code.prompt.md`
- `generate-unit-tests.prompt.md`
- `create-readme.prompt.md`
- `onboarding-plan.prompt.md`
