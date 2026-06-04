# Approach - Version 13.0.0: Smart Notification Engine, Advanced Document Intelligence & API Gateway Integration Hub

## Recommended Approach

### 1. Architectural Strategy
- Ensure service modules are self-contained and expose clear functional APIs.
- Avoid introducing circular dependencies on invoice routers.
- Maintain transactional consistency when reading from SQLite database paths.

### 2. Integration Design & Patterns
1. **Notification Scheduler**:
   - Poll upcoming dates on system boot and generate calendar notifications for the active user session.
   - Save alert records to `NotificationAlert` table in database.
2. **Document Classification Logic**:
   - Use naive Bayes or simple dictionary mapping on item names to assign tags (e.g. 'xăng', 'dầu' -> 'Fuel/Transport').
3. **REST Gateway Authorization**:
   - API Keys are stored as hashed records in the database.
   - Implement rate limits per key in memory using a fast token-bucket check.

---

## Risk Map & Mitigation Strategies

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Dynamic data parsing exceptions | Medium | Add structured validation constraints and catch exceptions gracefully. |
| Performance bottlenecks during batch processing | High | Execute large data imports inside background threads or scheduled queues. |
| Inaccurate tax computation | Critical | Cross-verify results with official Ministry of Finance calculators and write extensive tests. |
