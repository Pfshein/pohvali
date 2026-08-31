# CI Quality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a secret-free GitHub Actions workflow that runs the repository's complete frontend and backend quality checks for pull requests and pushes to `main`.

**Architecture:** Use two independent Ubuntu jobs so frontend and backend failures are isolated and visible. Each job installs only its own toolchain, uses the official dependency cache, and runs the same commands documented in `AGENTS.md` and used locally.

**Tech Stack:** GitHub Actions, Node.js 24, npm, Python 3.12, pip, React/Vite checks, Ruff, Pytest.

**Spec:** `docs/backlog.md` — `PH-002 · P0 · CI quality gate`.

## Global Constraints

- Run on pull requests and pushes to `main`, with optional manual dispatch.
- Grant the workflow only `contents: read` permission.
- Do not require repository secrets or production environment variables.
- Cache npm from `frontend/package-lock.json` and pip from `backend/pyproject.toml`.
- Frontend gate is exactly `npm run check` from `frontend/`.
- Backend gates are exactly `ruff check .` and `pytest` from `backend/`.
- Do not add deployment, Docker publishing, database services, or external actions beyond official `actions/*` setup actions.

---

### Task 1: GitHub Actions quality gate

**Files:**
- Create: `.github/workflows/ci.yml`
- Modify: `README.md`

**Interfaces:**
- Consumes: `frontend/package-lock.json`, `frontend/package.json`, `backend/pyproject.toml`.
- Produces: GitHub check jobs named `Frontend` and `Backend`.

- [x] **Step 1: Add the workflow**

Create `.github/workflows/ci.yml` with:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  frontend:
    name: Frontend
    runs-on: ubuntu-latest
    timeout-minutes: 10
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-node@v6
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run check

  backend:
    name: Backend
    runs-on: ubuntu-latest
    timeout-minutes: 10
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: backend/pyproject.toml
      - run: python -m pip install --upgrade pip
      - run: python -m pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest
```

- [x] **Step 2: Document the quality gate**

Add a `Проверки` section to `README.md` listing the local frontend and backend commands and explaining that GitHub Actions runs both automatically without application secrets.

- [x] **Step 3: Validate workflow syntax and local parity**

Run:

```powershell
docker run --rm -v "${PWD}:/repo" rhysd/actionlint:latest -color /repo/.github/workflows/ci.yml
cd frontend
npm run check
cd ../backend
ruff check .
pytest
```

Expected: actionlint exits `0`; frontend lint/typecheck/tests/build pass; backend Ruff and Pytest pass.

- [x] **Step 4: Review the final workflow**

Confirm both jobs use official `actions/*` actions, caches have explicit dependency paths, no `${{ secrets.* }}` expression exists, and no deploy/publish permissions were added.

## External activation

After the repository is pushed to GitHub and the workflow has run once, enable a `main` branch
rule requiring the `Frontend` and `Backend` status checks. This repository currently has no
remote, so that GitHub-side rule cannot be configured from this checkout yet.
