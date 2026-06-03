# US-007 CAPTCHA Caching & Prefetch Queue

## Status

completed

## Lane

normal

## Product Contract

To eliminate the 1-3 seconds network latency when retrieving a GDT CAPTCHA on page load or retry login loops, the system will maintain a background daemon worker thread that pre-fetches and pre-solves up to 2 GDT CAPTCHAs.

## Relevant Product Docs

- [02_specification.md](file:///d:/LearnAnyThing/Webapp%20XML/02_specification.md)
- [03_implementation_plan.md](file:///d:/LearnAnyThing/Webapp%20XML/03_implementation_plan.md)

## Acceptance Criteria

- **AC 1: Daemon Worker**: A daemon thread checks the prefetch queue length every few seconds. If the length is less than 2, it fetches and solves a CAPTCHA.
- **AC 2: Expiration Control**: Cached CAPTCHA entries expire after 120 seconds to prevent using stale session tokens from GDT.
- **AC 3: Instant Retrieval**: When the frontend asks for a CAPTCHA, or the retry loop requests one, pop a pre-solved CAPTCHA from the queue immediately if available.
- **AC 4: Fallback**: If the prefetch queue is empty, fall back to fetching a new CAPTCHA synchronously.

## Design Notes

- **Queue Storage**: List of solved CAPTCHA dictionaries in `auth/captcha.py`.
- **Worker Thread**: Daemon thread started during app startup (`app.py`).

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Tests verifying cache insertion, expiry, and popping mechanics in `tests/test_captcha_queue.py`. |
| Integration | Tests showing pre-solved cache hits inside auth route. |

## Harness Delta

- Updated `PROGRESS_TRACKER_INVOICE_WEBAPP.md` with prefetching tasks.

## Evidence

Validated using `tests/test_captcha_queue.py` which passes successfully:
- `test_pop_empty_queue` (AC 4)
- `test_pop_valid_and_expired_items` (AC 2, AC 3)
- `test_prefetch_worker_populates_queue` (AC 1)
- `test_route_uses_prefetched_captcha` (AC 3, Integration layer)

