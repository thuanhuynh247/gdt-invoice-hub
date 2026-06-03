# US-184 Multi-Signature Approval Workflows

## Status

implemented

## Lane

normal

## Product Contract

The application must enforce a customizable multi-signature approval routing chain (e.g. Accountant -> Chief Accountant -> Director) for outgoing e-invoices, verifying user signatures at each stage and preventing digital portal submission until all approvals are secured.

## Relevant Product Docs

- `docs/product/v15_roadmap.md`

## Acceptance Criteria

- [x] Support creating approval workflow templates with sequential or parallel approvers.
- [x] Implement signature recording for each approver in the workflow chain.
- [x] Block outgoing invoice signing and GDT portal submission until the final approval signature is recorded.
- [x] Expose API endpoint `POST /api/approval/workflows` to configure and track approval states.
- [x] Display an approval progress bar and state indicators on invoice creation panel.
- [x] Write unit tests verifying approval state transitions and signing blocks.

## Design Notes

- **Module**: `auth/approval_workflow.py` and `invoices/service.py` modification.
- **Database table**: Create `ApprovalWorkflow` and `ApprovalSignature` tables or map approval states in database schema.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v15_approval_workflow.py` checking sequential and parallel approval routing |
| Integration | Submitting an unapproved invoice draft to the signing service throws an unauthorized approval block error |
