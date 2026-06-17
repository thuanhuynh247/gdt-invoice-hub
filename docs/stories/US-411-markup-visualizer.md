# Story Specification: US-411 — Interactive SVG Arm's Length Visualizer & Markup Sensitivity Modeler

## 📋 Context & Business Value
To make compliance intuitive for financial teams, the system needs an interactive, zero-dependency visualizer rendering the arm's length range. The visualizer plots the target transaction's markup against the interquartile range (35th to 75th percentiles) and provides interactive sliders to model price sensitivity, immediately calculating projected tax adjustments.

---

## 🎯 Acceptance Criteria
- **Zero-Dependency SVG Visualizer**:
  - Build a custom SVG rendering the benchmark distribution: 35th percentile, Median (50th), and 75th percentile.
  - Plot a marker indicating the taxpayer's current markup.
  - Color-code risk zones: red/amber for out-of-range, green for compliant.
- **Sensitivity Sandbox Dashboard UI**:
  - Expose an interactive slider allowing the user to dynamically modify the related-party transaction markup percentage.
  - Update the SVG position, risk classification, tax adjustment, and penalty projections on the fly.
  - Render inside the compliance portal with smooth transitions and glassmorphism styling.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\python -m pytest tests/test_v30_features.py -k test_markup_visualizer_routes"
  ```
