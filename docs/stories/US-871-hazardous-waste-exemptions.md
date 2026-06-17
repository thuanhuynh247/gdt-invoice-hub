# Story US-871: Hazardous Waste Exemption & Small Generator Auditor

## Business Need
Decree No. 08/2022/NĐ-CP provides regulatory relief for small generators producing less than 600 kg of hazardous waste per year. These generators do not require a formal hazardous waste license (only simple registration), exempting them from the licensing fee. Academic labs are also exempt from licensing fees for educational waste.

## Technical Requirements
- Support exemption validation:
  1. Small generator check: If annual hazardous waste generation `annual_weight_kg < 600`, the facility is exempt from licensing fees (set licensing fee to 0).
  2. Research/academic lab check: If `is_research_lab = true`, licensing fee is **100% exempt**.
- Disposal fees are still calculated on the actual weight, but licensing fees are waived.

## Acceptance Criteria
- Set licensing fee component to 0 if small generator or research lab criteria are met.
- Correctly log the exemption reason in the compliance audit trail.
