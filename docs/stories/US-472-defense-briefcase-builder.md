# Spec: US-472 — Automated Audit Defense Briefcase & Auto-Correction Package

## Status
completed

## Lane
normal

## Product Contract

The system provides a service to build a downloadable **Audit Defense Briefcase** zip file aggregating all relevant support documents (XML, PDFs, matching bank statement transactions, AI defense letter) for selected high-risk invoices, and automatically generates GDT Form 04/SS-HĐĐT correction XML when tax rates or buyer details contain anomalies.

## Acceptance Criteria

- [x] Backend endpoint `/api/compliance/defense-package` accepts a list of invoice UUIDs/numbers.
- [x] Packs matching invoice XMLs, generated invoice PDFs, matching bank transaction lines, and AI-compiled defense descriptions into a single ZIP archive.
- [x] Auto-generates the official GDT Form 04/SS-HĐĐT XML schema template matching GDT specifications for correction/replacement invoice notification.
- [x] Exposes a download button in the web application UI.
