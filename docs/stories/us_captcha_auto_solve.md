# US-005 Auto-Solving GDT Captcha Offline

## Status

completed

## Lane

normal

## Product Contract

The application will automatically solve GDT SVG captchas offline in-memory using `ddddocr` and `svglib` without requiring manual captcha entry. It will transparently retry on incorrect captcha responses from GDT.

## Relevant Product Docs

- [02_specification.md](file:///d:/LearnAnyThing/Webapp%20XML/02_specification.md)
- [03_implementation_plan.md](file:///d:/LearnAnyThing/Webapp%20XML/03_implementation_plan.md)

## Acceptance Criteria

- **AC 1: Noise Filtering**: Correctly parse the SVG XML, identifying and filtering out noise paths (paths with `fill="none"` or containing `stroke`).
- **AC 2: In-Memory PNG Rendering**: Render the remaining clean SVG paths into standard PNG bytes in-memory using `svglib` and `reportlab.graphics.renderPM`.
- **AC 3: Offline Solving**: Solve the PNG bytes using an offline `ddddocr` instance, cleaning up the string response to uppercase alphanumeric.
- **AC 4: Automatic Login / Sync Integration**: Integrate the captcha solving engine with the live login flow, auto-resolving captchas.
- **AC 5: Transparent Retry Mechanism**: Implement a retry loop (up to 5 attempts) when calling GDT endpoints. If GDT returns a 401 with a "Mã captcha không đúng" error, the system will fetch a new captcha, solve it, and retry login.
- **AC 6: Manual Fallback**: If `AUTO_SOLVE_CAPTCHA` is configured as `False` in `.env`, or if all retry attempts are exhausted, fall back to manual captcha input via the UI.

## Design Notes

- **Modules**:
  - `auth/captcha_solver.py` containing `solve_captcha_from_svg(svg_content: str) -> str`.
- **Configuration**:
  - Add `AUTO_SOLVE_CAPTCHA` (boolean, default: True) to `.env` and `config.py`.
- **API integration**:
  - Update routes handling authentication and live fetching to use `solve_captcha_from_svg()` and execute retry loops.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Tests verifying noise path removal, PNG generation, and text matching in `tests/test_captcha_solver.py::test_svg_noise_filtering_and_sorting` and `test_solve_captcha_mock_text_tag`. |
| Integration | Tests simulating incorrect captchas followed by successful solves and retries in `tests/test_captcha_solver.py::test_api_login_auto_solve_loop`. |

## Harness Delta

- Added dependencies: `ddddocr`, `svglib`, `reportlab`, `lxml` to requirements.txt.

## Evidence

Unit and integration tests passed:
```text
tests\test_captcha_solver.py ...                                         [ 31%]
======================= 44 passed, 2 warnings in 3.57s ========================
```

