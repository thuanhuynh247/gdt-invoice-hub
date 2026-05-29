# US-006 Asynchronous Batch Invoice Downloading

## Status

completed

## Lane

normal

## Product Contract

The application will process GDT batch invoice downloads asynchronously in a background thread to prevent HTTP gateway timeouts (504) and freezing the frontend. The user will see a real-time progress bar tracking the fetch, audit, and zip packaging process, and download the finished ZIP archive once completed.

## Relevant Product Docs

- [02_specification.md](file:///d:/LearnAnyThing/Webapp%20XML/02_specification.md)
- [03_implementation_plan.md](file:///d:/LearnAnyThing/Webapp%20XML/03_implementation_plan.md)

## Acceptance Criteria

- **AC 1: Background Execution**: Triggering a batch download spawns a daemon thread, returning a unique task ID immediately with a 202 Accepted status.
- **AC 2: Status Polling API**: Provide `/api/invoices/batch-download/status/<task_id>` which reports status (`running`, `completed`, `failed`), total invoices, completed invoices, and progress percentage.
- **AC 3: Streamlined Zip Retrieval**: Deliver the packaged ZIP from `/api/invoices/batch-download/download/<task_id>` only when status is `completed`, and remove the task data from memory immediately post-download to prevent leaks.
- **AC 4: Progress UI Overlay**: Frontend modal displays a progress bar and label reflecting real-time task progress.
- **AC 5: Error Handling**: If the fetch fails, capture the error string and display it clearly inside the UI progress modal.

## Design Notes

- **Task Storage**: In-memory `dict` protected by a thread lock.
- **End Points**:
  - `POST /api/invoices/batch-download` -> Starts task, returns `{"task_id": "...", "status": "running"}`.
  - `GET /api/invoices/batch-download/status/<task_id>` -> Returns status JSON.
  - `GET /api/invoices/batch-download/download/<task_id>` -> Downloads completed ZIP.
- **UI Element**: Bootstrap modal with `.progress-bar`.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Test that task dict manages task lifecycle states. |
| Integration | Test `/api/invoices/batch-download` spawns thread and updates status and delivers correct ZIP bytes. |

## Harness Delta

- Updated `PROGRESS_TRACKER_INVOICE_WEBAPP.md` with new Phase 5 task items.

## Evidence

Validated using `tests/test_async_download.py` which passes successfully:
- `test_batch_download_async_lifecycle` (AC 1, AC 2, AC 3, AC 4)
- `test_batch_download_async_failure_reporting` (AC 5)
- `test_batch_download_async_missing_task` (Boundary check)

