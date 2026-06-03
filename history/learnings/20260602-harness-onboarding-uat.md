# Compounding Learnings: Onboarding & UAT Verification (US-212)

**Feature Slug:** harness_onboarding_uat
**Date Completed:** 2026-06-02
**Author:** Antigravity (Advanced Agentic Coding Specialist)

## 1. Architectural Lessons & Takeaways

### A. Dynamic SQLite Decoding Factory (`decode_smart`)
- **Lesson:** In Windows environments, SQLite databases storing Vietnamese characters (e.g. from government portals or XML files) can contain mixed CP1258, Windows-1252, or UTF-8 encodings. Standard Python `sqlite3` queries throw `sqlite3.OperationalError` if they encounter bytes they cannot decode into standard UTF-8.
- **Pattern:** Always configure a resilient custom `text_factory` callback:
  ```python
  def decode_smart(x):
      try:
          return x.decode('utf-8')
      except Exception:
          try:
              return x.decode('cp1258')
          except Exception:
              return x.decode('utf-8', errors='replace')
  conn.text_factory = decode_smart
  ```
  This guarantees that queries do not crash during automated trace, story, or auditing executions.

### B. Mock-Based Offline Test Isolation
- **Lesson:** Integration tests for external government services (like GDT portal) must be isolated behind high-fidelity mock environments. 
- **Pattern:** Using `GDT_USE_MOCK=true` allows the application to execute offline with 100% predictable outcomes, while keeping the pre-flight checks fully clean without requiring actual internet routing or captcha solving.

---

## 2. Technical Decisions & Refinements

### A. Pre-flight Security Configurations
- **Debug Mode Disabling:** `FLASK_DEBUG` must be set to `false` in production `.env` to prevent arbitrary code execution vulnerabilities in UAT/Production.
- **Story Status Synchronization:** Harness DB stores state. Stories must be updated to `implemented` to resolve pre-flight validation warnings.

---

## 3. Critical Patterns Promoted

1. **Smart Text Factory for SQLite on Windows:**
   - Always hook up decode_smart on Windows to avoid UTF-8 decoding operational errors with Vietnamese characters.
2. **Automated UAT Report Scaffolding:**
   - Programmatically generate UAT report files (`UAT_REPORT_*.md`) based on trace execution and git metadata to keep auditing logs consistent.
