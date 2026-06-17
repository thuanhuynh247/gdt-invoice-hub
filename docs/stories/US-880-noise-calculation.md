# Story US-880: Core Noise & Vibration Pollution Surcharge Engine

## Business Need
Vietnam's Law on Environmental Protection 2020 penalizes industrial facilities exceeding statutory limits for noise and vibration under QCVN 26:2010/BTNMT and QCVN 27:2010/BTNMT. Surcharges are scaled by the degree of exceedance.

## Technical Requirements
- Input parameters: measured noise level (`noise_db`), measured vibration level (`vibration_m_s2`), and shift (`day` or `night`).
- Limits:
  - Day shift (06:00 - 21:00): Noise limit **70 dBA**
  - Night shift (21:00 - 06:00): Noise limit **55 dBA**
  - Vibration limit: **0.055 m/s²** (same for day and night).
- Calculations:
  - Noise exceedance = Max(0, `noise_db` - limit)
  - Vibration exceedance = Max(0, `vibration_m_s2` - limit)
  - Rates:
    - Excess noise: **100,000 VND per dBA** exceedance.
    - Excess vibration: **5,000,000 VND per 0.01 m/s²** exceedance (e.g. 0.01 exceedance is 5,000,000, 0.02 is 10,000,000, etc.).
    - Night shift multiplier: Surcharges computed during `night` shift are subject to a **1.5x multiplier**.
  - Total Surcharge = (Noise Surcharge + Vibration Surcharge) * shift_multiplier.

## Acceptance Criteria
- Correct surcharge calculations for day shift noise and vibration exceedances.
- Correct 1.5x night shift multiplier applied to both surcharges.
- Surcharge must be 0 if levels are below statutory limits.
