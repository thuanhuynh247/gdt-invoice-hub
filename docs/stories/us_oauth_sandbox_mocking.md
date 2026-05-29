# Multi-Tenant OAuth2 Sandbox Mocking for Cloud Sync

## Status

completed

## Lane

tiny

## Product Contract

Introduce a centralized, robust local OAuth2 sandbox mock controller in pytest fixtures to intercept third-party cloud synchronization endpoints (Google Drive & Microsoft OneDrive). This allows testing of offline credential exchanges, directory traversal, dynamic folder creation, and multi-tenant file syncing under realistic simulated network conditions and failure modes.

## Relevant Product Docs

- `docs/HARNESS_BACKLOG.md`
- `docs/stories/backlog.md`

## Acceptance Criteria

- **AC 1: Centralized OAuth2 Sandbox**: An `OAuth2Sandbox` class in `tests/conftest.py` managing stateful token mappings, folder IDs, and virtual files.
- **AC 2: Pytest Fixture Interceptor**: A `pytest` fixture named `oauth_sandbox` that automatically intercepts all module-level calls to `requests.get`, `requests.post`, `requests.put`, and `requests.request` during test runs, eliminating the need for boilerplate `@patch` decorators.
- **AC 3: Failures and Expiration Simulation**: Methods to simulate token expiration, invalid credentials, and server upload/creation failures to verify token refresh and recoverability logic.
- **AC 4: Request Tracing & Verification**: Recording and verification of outgoing endpoints, authorization headers, request bodies, and file payloads inside tests.
- **AC 5: Clean Integration**: Refactoring of `tests/test_cloud_sync.py` to utilize `oauth_sandbox` for simplified, resilient, and more descriptive testing.

## Design Notes

- **Intercept Mechanism**: Store original `requests` methods, overwrite them during fixture yield, and restore them during teardown.
- **Mock Handlers**: Parse target URLs dynamically:
  - Token Endpoints: `oauth2.googleapis.com/token` and `login.microsoftonline.com/common/oauth2/v2.0/token`.
  - Google Drive Files API: `www.googleapis.com/drive/v3/files` and `/upload/drive/v3/files`.
  - Microsoft Graph API: `graph.microsoft.com/v1.0/me/drive/root`.
- **Encryption validation**: Decrypt taxpayers credentials fetched from simulated session/database dynamically inside sync flows.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit / Integration | Rewrite target tests in `tests/test_cloud_sync.py` using `oauth_sandbox` to cover refresh flows, file upload sequences, and token expiration errors. |

## Harness Delta

- Updated `docs/HARNESS_BACKLOG.md` status to `implemented`.
- Updated `docs/stories/backlog.md` with E35 / backlog item details.

## Evidence

Completed and validated via local test suites:
```powershell
python -m pytest tests/test_cloud_sync.py
```
- `test_sync_invoice_to_cloud_with_sandbox` verifies standard successful loopback intercept, token retrieval, folder traversal, and multipart uploads.
- `test_sync_invoice_to_cloud_sandbox_failures` verifies network connection errors, token refresh failures, folder creation errors, file upload endpoint failures, and 401 Unauthorized credential validation.

