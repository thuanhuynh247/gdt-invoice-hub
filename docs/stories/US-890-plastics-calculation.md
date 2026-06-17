# Story US-890: Core Single-Use Plastics & Ocean Pollution Levy Engine

## Business Need
Under Decree No. 08/2022/NĐ-CP, Vietnam imposes an environmental levy on single-use plastics, non-biodegradable bags, and expanded polystyrene (EPS) containers to fund plastic reduction programs and ocean cleanups.

## Technical Requirements
- Input parameters: plastic type (`bag`, `straw_cup`, `eps_box`) and weight/quantity.
- Rates:
  - `bag` (non-biodegradable plastic bags): **150,000 VND / kg**
  - `straw_cup` (single-use cups, plates, straws): **500 VND / unit**
  - `eps_box` (expanded polystyrene food containers): **2,000 VND / unit**
- Surcharge calculations must validate input values to be positive numbers.

## Acceptance Criteria
- Correct levy calculations for all three categories.
- Raise validation errors for invalid category types or negative values.
