# Story Specification: US-393 — Interactive Tax Risk Radar SVG & Audit Advisory Dashboard UI

## 📋 Context & Business Value
Users need to visualize audit exposure quickly. This story implements a visual dashboard showing a native SVG radar chart of the 5 risk vectors and providing interactive recommendations.

---

## 🎯 Acceptance Criteria
- **SVG Radar Chart Renderer**:
  - Draw a 5-axis visual radar chart utilizing inline HTML `<svg>` and `<polygon>` elements, mapping the 5 compliance dimensions dynamically based on calculated scores.
  - Draw grid lines, axis labels, and tooltip interaction zones.
- **Audit Advisory Interface**:
  - Render a side panel list of specific legal advice (citing Decree 123/NĐ-CP, Circular 80/TT-BTC, or Decree 132/NĐ-CP) corresponding to flagged risk domains.
  - Support exporting the visual dashboard view to a PDF audit memo structure.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\python -m pytest tests/test_v27_features.py -k test_risk_radar_ui"
  ```
