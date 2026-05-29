# US-015 Encrypted Session Credentials & Auto-Refresh Session

## Status

implemented

## Lane

normal

## Product Contract

The application should encrypt GDT taxpayer credentials (password) before storing them in the session cookie to prevent local plaintext credential exposure. If a background process or page request encounters a 401 Unauthorized / expired JWT token from GDT, it should automatically use the decrypted credentials, fetch/solve a pre-buffered CAPTCHA, and re-authenticate to refresh the JWT session transparently without logging out or prompting the user.

## Relevant Product Docs

- `docs/product/auth.md`
- `01_constitution.md` (Principle 4: Security Over Convenience)

## Acceptance Criteria

- [x] Add `cryptography` to `requirements.txt` to support AES (Fernet) encryption.
- [x] Implement a helper module `auth/crypto.py` containing:
  - Encryption using `cryptography.fernet.Fernet` with a key derived from Flask's `SECRET_KEY` (using PBKDF2/SHA256 to ensure determinism).
  - Encrypt and Decrypt functions for credentials.
- [x] Modify `POST /api/auth/login` to encrypt and store the user's password in `session["encrypted_password"]` upon successful authentication.
- [x] Implement automatic re-authentication (session refresh) when a 401 error or GDT session expiry is encountered during API calls.
- [x] Ensure background async batch download threads can automatically re-authenticate and refresh the GDT JWT if it expires mid-download.
- [x] Write tests verifying encryption/decryption functions and auto-refresh logic.

## Design Notes

- **Encryption Module**: `auth/crypto.py` using Fernet.
- **API integration**: Intercept `GDTIntegrationNotReadyError` or 401 status in routes and trigger auto-login.
- **UI surfaces**: Transparent backend logic, no UI changes required.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_secure_credentials.py` checks cryptography functions |
| Integration | Auto-refresh triggered and successfully completes search / download when mock JWT expires |

## Harness Delta

N/A

## Evidence

- **`tests/test_secure_credentials.py`**:
  - `test_cryptography_reversible`: Verified that credentials encrypted with AES-CBC/Fernet can be decrypted back to plaintext.
  - `test_cryptography_handles_empty`: Verified that encrypting/decrypting empty strings/None does not cause crashes.
  - `test_login_stores_encrypted_password`: Verified that the user's credentials are encrypted before storing them in the Flask session cookie.
  - `test_auto_refresh_triggered_on_401`: Verified that the automatic refresh logic triggers transparent re-authentication on 401 errors, using pre-buffered captchas, and retries the operations successfully.
- **Test Integrity**: All 55 tests in the test suite passed with 78% code coverage via `scripts/validate.bat`.

