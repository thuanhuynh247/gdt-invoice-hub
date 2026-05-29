# US-024: Recurring Scheduled Exports and Email Delivery

## Status

completed

## Lane

normal

## Product Contract

The application must support setting up automated schedules (daily or weekly) to search for GDT invoices, compile them into an Excel spreadsheet, and send the report automatically to a designated email address (such as the company's Accountant or Director) using SMTP.

## Relevant Product Docs

- [02_specification.md](file:///d:/LearnAnyThing/Webapp%20XML/02_specification.md)

## Acceptance Criteria

- [x] Provide an Email & Schedule Configuration tab/modal in the settings panel.
- [x] Users can enter SMTP settings (Host, Port, Username, Password, SSL/TLS) and target recipient email.
- [x] Users can toggle scheduling on/off and select interval (Daily at Hour X, or Weekly on Day Y).
- [x] A background task/daemon (using APScheduler or custom background loop) runs at the scheduled time.
- [x] When triggered, the job fetches invoices for the preceding period (e.g. past day or past week).
- [x] Creates a formatted Excel sheet with the results.
- [x] Dispatches an email with the Excel attachment to the target email.
- [x] Logs successes and failures in a persistent log database or local text file for audit.

## Design Notes

- **Libraries**: `APScheduler` for python job scheduling, `smtplib` for email delivery.
- **Settings Store**: Encrypted credentials and config saved in `invoices_db.json` or config file.
- **Security**: SMTP password must be symmetrically encrypted before storage using cryptography key.
- **UI Surfaces**:
  - A settings page layout for configuring SMTP, test emails, and scheduled times.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Tests verifying scheduler trigger logic and Excel compilation |
| Integration | Tests verifying email dispatcher with a mock SMTP server |
| E2E | Manual or automated test verifying mail delivery receipt |

## Harness Delta

None.

## Evidence

- Unit & integration tests in [test_scheduler.py](file:///d:/LearnAnyThing/Webapp%20XML/tests/test_scheduler.py) pass successfully.
- Local validation runs verify full integration of schedule and SMTP settings.
