# US-155 Consolidated Executive Slide Exporter

## Status

planned

## Lane

normal

## Product Contract

The application must automatically generate executive briefing slide decks (PowerPoint) or PDF portfolios containing consolidated multi-entity performance metrics, risk heatmaps, VAT projections, and compliance summaries. Each exported report includes a cryptographic validation block linking back to the original tenant database states.

## Relevant Product Docs

- `docs/product/v12_roadmap.md`

## Acceptance Criteria

- [ ] Implement API endpoint `GET /api/reports/executive-brief` generating the consolidated presentation.
- [ ] Generate professional slide decks with group summary, entity comparison, risk heatmap, and tax projections.
- [ ] Support export to PowerPoint (.pptx) and PDF formats.
- [ ] Embed a SHA-256 integrity block in the final slide mapping back to original data snapshots.
- [ ] Write tests verifying file generation, content correctness, and integrity hash accuracy.

## Design Notes

- **Export engine**: `export/service.py` — new function `generate_executive_brief()`.
- **Slide library**: `python-pptx` for PowerPoint generation; existing PDF pipeline for PDF export.
- **Template**: Structured slide layouts (title, KPI grid, heatmap, projections, integrity footer).

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Verify generated .pptx file is valid and contains expected slide count |
| Integration | Verify SHA-256 block matches recalculated hash of source data |
