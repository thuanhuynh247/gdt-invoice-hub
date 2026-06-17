# US-671: IET Exemption & Threshold Auditor

## Description
As a tax compliance auditor, I want to verify if import/export items qualify for exemptions, specifically for goods processed under contract, temporary imports for re-export, and low-value gifts, so that the company does not overpay border taxes.

## Acceptance Criteria
- Set duty to 0 and record `is_exempt = True` if the goods purpose is "processing contract" (hàng gia công).
- Set duty to 0 and record `is_exempt = True` if the goods purpose is "temporary import" (tạm nhập tái xuất).
- Set duty to 0 and record `is_exempt = True` if the total declared value (Quantity × Unit Price) of a "gift" is ≤ 2,000,000 VND.
- Save exemption status and auditing logs in `iet_calculations` database table.
