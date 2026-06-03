# US-014 Automated Validation Runner & CI/CD Integration

## Status

completed

## Lane

tiny

## Product Contract

Introduce a standardized, automated validation script (both locally for developers and on CI/CD pipeline) to enforce python syntax checks, test suite execution with pytest, and code coverage checks (>70%). The checks must block commits or deployments if any test fails or syntax errors are detected.

## Relevant Product Docs

- `AGENTS.md` (Agent Operating Guide)
- `docs/HARNESS_README.md` (Expected checks)

## Acceptance Criteria

- [x] Create `scripts/validate.bat` script for Windows that activates the virtual environment, compiles python files to check syntax, runs `pytest` with coverage, and prints status.
- [x] Create `scripts/validate.sh` script for Linux/macOS that does the same.
- [x] Create `.github/workflows/ci.yml` GitHub Actions workflow file to run linting/testing automatically on pull requests and commits to main.
- [x] Validate that scripts execute successfully and exit with code 0 on passing tests, or non-zero on failing tests.

## Design Notes

- **Scripts Directory**: All validation code goes under `scripts/`.
- **Command mappings**:
  - Syntax check: `python -m compileall -q .`
  - Test suite run: `python -m pytest -v --cov=auth --cov=invoices --cov=export --cov=app --cov-report=term-missing`
- **Actions Trigger**: Trigger on push/pull_request to main.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | N/A (Meta-automation) |
| Integration | Validation scripts return exit code 0 when all tests pass |
| Platform | Executing `scripts/validate.bat` locally completes with green success status |
| Release | GitHub Actions runner executes pytest suite successfully |

## Harness Delta

- Added automated pre-commit / pre-deployment validation gates.
- Simplified agent validation loop: agents can now run `scripts/validate.bat` instead of complex inline commands.

## Evidence

Running `scripts\validate.bat` locally on Windows:
```text
===================================================
[HARNESS VALIDATE] Running Local Validation Gate...
===================================================
[1/3] Activating virtual environment...
[2/3] Checking python syntax in codebase...
[SUCCESS] Python syntax is valid.
[3/3] Running pytest suite with coverage...
collected 51 items
tests/test_async_download.py::test_batch_download_async_flow PASSED
tests/test_auth.py::test_login_success_sets_session PASSED
...
TOTAL                     1302    302    77%
======================= 51 passed, 2 warnings in 42.48s =======================
===================================================
[SUCCESS] All validation checks passed successfully!
===================================================
```
