# Story US-860: Core Industrial Wastewater Surcharge Engine

## Business Need
Under Decree No. 53/2020/NĐ-CP, manufacturing plants discharging industrial wastewater must pay quarterly environmental protection fees based on discharge volume and pollutant concentrations.

## Technical Requirements
- Input parameters: discharge volume (`volume_m3`), concentrations of COD (`cod_mg_l`), TSS (`tss_mg_l`), and heavy metals: Lead (`pb_mg_l`), Mercury (`hg_mg_l`), Cadmium (`cd_mg_l`).
- Calculations:
  - Daily volume threshold: If total volume is less than 20 m3/day, apply the flat annual fee of **1,500,000 VND / year** (divided by 4 for quarterly calculation, i.e., 375,000 VND).
  - Otherwise, compute fees based on load (kg):
    - Pollutant Load (kg) = Volume (m3) * Concentration (mg/L) / 1,000.
    - Rates:
      - COD: **2,000 VND / kg**
      - TSS: **4,000 VND / kg**
      - Mercury (Hg): **20,000,000 VND / kg**
      - Lead (Pb): **1,000,000 VND / kg**
      - Cadmium (Cd): **10,000,000 VND / kg**
  - Reject negative concentration levels or negative volume.

## Acceptance Criteria
- Correct flat quarterly rate of 375,000 VND for small dischargers (< 20m3/day average).
- Accurate load-based variable fees for large dischargers.
