# Constitution: Invoice Download Webapp
**Project Code**: INVOICE-WEBAPP-PLAN-A  
**Version**: 1.0  
**Date**: 2026-05-19  
**Owner**: Huỳnh Anh Thuận

---

## 🎯 Project Governing Principles

These principles guide all technical decisions, code quality standards, and implementation choices throughout the project lifecycle.

### PRINCIPLE 1: Pragmatic Over Perfect
- **Statement**: Choose simple, working solutions over complex elegant ones
- **Rationale**: Project timeline is 4-5 weeks; user is learning Python simultaneously. Complexity increases risk of stalling
- **Application**: 
  - Use vanilla Python/JS over fancy frameworks
  - Prefer 3-line working code over 1-line elegant code
  - Implement features to 80% completeness, not 100%
  - No premature optimization

### PRINCIPLE 2: Learning-First Mindset
- **Statement**: Every line of code must be educational for non-programmer
- **Rationale**: User has zero coding background. Code quality includes explainability
- **Application**:
  - Every function must have docstring explaining "what" and "why"
  - Comments explain complex logic, not obvious code
  - Variable names are clear, never cryptic (username not u, not user_auth_token)
  - Code structure mirrors mental model (data flows top-to-bottom)
  - No magic numbers or unexplained patterns
  - Provide "why it works" explanations, not just "how to use"

### PRINCIPLE 3: Working Code Always Available
- **Statement**: End of each phase = runnable, testable software
- **Rationale**: User needs proof-of-progress; integration issues caught early
- **Application**:
  - No multi-hour black holes where code can't run
  - Each route must be testable with curl/Postman
  - Frontend must work without backend for UI testing
  - Broken tests must be fixed same day, not "we'll fix later"
  - User can demo each week's work

### PRINCIPLE 4: Security Over Convenience
- **Statement**: Never store credentials in code; never skip error handling
- **Rationale**: Financial data (invoices) + Vietnamese government system = high sensitivity
- **Application**:
  - All credentials in `.env`, never in code
  - Session management follows best practices (expiry, refresh)
  - gdt.gov.vn API calls always error-checked
  - User-facing errors are friendly, not exposing stack traces
  - Data validation on every input (dates, user input, API responses)
  - No plain HTTP; use HTTPS for production-ready mindset

### PRINCIPLE 5: Clear Communication, No Assumptions
- **Statement**: When in doubt, ask; never silently fail or guess
- **Rationale**: User is non-technical; silent failures kill trust and cause debugging nightmares
- **Application**:
  - Errors show specific reason ("Invalid date format: must be YYYY-MM-DD" not "Error")
  - Loading states visible (spinners, disabled buttons)
  - Session timeouts logged and user notified immediately
  - API failures show retry options, not just "failed"
  - User sees progress (how many invoices downloaded, file being generated)

### PRINCIPLE 6: Testing as First-Class Citizen
- **Statement**: Code is not done until tested
- **Rationale**: Prevents "it worked yesterday" bugs; gives confidence for future changes
- **Application**:
  - Every route has ≥2 test cases (success + error)
  - Test data mirrors real gdt.gov.vn responses
  - Tests can run locally without external dependencies
  - 70%+ code coverage required before phase completion
  - Manual testing checklist required before next phase

### PRINCIPLE 7: Documentation is Part of Code
- **Statement**: If it's not documented, it's not done
- **Rationale**: Future maintainer is future you; user needs to understand what you built
- **Application**:
  - README explains what, why, how to run
  - API documentation with example requests/responses
  - Architecture diagrams for complex flows
  - Troubleshooting FAQ based on actual errors encountered
  - Code comments explain *why*, not *what*

### PRINCIPLE 8: Performance Mindset, Not Optimization Obsession
- **Statement**: Code must be fast enough, not fastest possible
- **Rationale**: Balance user experience with development speed
- **Application**:
  - Page loads <3s
  - Excel export <5s for 1000 rows
  - gdt.gov.vn API calls timeout after 30s (not instant success expected)
  - No premature caching; only cache after proving slowness
  - Monitor but don't optimize until there's a visible problem

### PRINCIPLE 9: User Experience Consistency
- **Statement**: Every page/feature must feel like one product
- **Rationale**: Cohesive UI reduces learning curve for non-technical user
- **Application**:
  - Consistent color scheme (Bootstrap 5 defaults)
  - Consistent form patterns (all inputs same height, spacing)
  - Consistent error/success messages (location, styling, tone)
  - Consistent terminology (don't call it "invoice" then "bill" then "document")
  - Mobile-friendly design (not desktop-only)
  - Dark mode optional but consistent if implemented

### PRINCIPLE 10: Dependency Minimalism
- **Statement**: Use fewest, most stable libraries possible
- **Rationale**: Fewer dependencies = fewer breaking changes = longer project lifespan
- **Application**:
  - Flask (lightweight, mature, well-documented)
  - requests (HTTP library standard)
  - openpyxl (only mature Excel library needed)
  - Selenium (only for browser automation if necessary)
  - Bootstrap 5 CDN (not npm package bloat)
  - Vanilla JavaScript (no jQuery, Vue, React unless absolutely needed)
  - No trendy libraries; use what's been stable for 3+ years

---

## 🏗️ Development Standards

### Code Quality Checklist
- [ ] Passes linting (consistent formatting)
- [ ] Functions have docstrings
- [ ] No commented-out code
- [ ] No hardcoded credentials
- [ ] No console.log() in production code (use proper logging)
- [ ] Variable names are clear and descriptive
- [ ] Functions do one thing well

### Testing Requirements
- [ ] Unit tests pass (pytest)
- [ ] Manual testing checklist completed
- [ ] Error cases tested (not just happy path)
- [ ] Real gdt.gov.vn data tested if possible
- [ ] Performance acceptable (<3s page load)

### Documentation Requirements
- [ ] README updated
- [ ] Code comments explain why, not what
- [ ] API endpoint documented (if new endpoint)
- [ ] Troubleshooting FAQ updated
- [ ] CHANGELOG updated

### Review Before Committing
- [ ] Does this follow principles 1-10?
- [ ] Is this understandable to non-programmer?
- [ ] Will this code work 6 months from now?
- [ ] Is error handling complete?
- [ ] Are credentials safe?

---

## 📋 Phase Gates

Before moving to next phase, answer YES to all:

**Phase Gate Template**:
```
[ ] All tasks from current phase completed
[ ] Code runs without errors
[ ] Tests pass (≥70% coverage)
[ ] Documentation complete
[ ] User understands what was built
[ ] No security issues identified
[ ] Performance acceptable
[ ] Code follows all 10 principles
```

---

## 🚨 Hard Stops (Blocker Conditions)

**STOP development immediately if**:
- 🔴 Credentials found in source code → remove immediately, never commit
- 🔴 Session data stored insecurely → redesign authentication
- 🔴 Error messages expose sensitive information → sanitize immediately
- 🔴 gdt.gov.vn API credentials exposed → change password, never commit
- 🔴 Feature works but is incomprehensible → rewrite for clarity

---

## 📊 Success Metrics

Project is successful when:
- ✅ Webapp runs on localhost:5000
- ✅ Can login to gdt.gov.vn system
- ✅ Can download invoices (single + batch)
- ✅ Can export to Excel with correct formatting
- ✅ 70%+ test coverage
- ✅ Complete documentation
- ✅ User can operate independently
- ✅ Code is understandable to someone learning Python
- ✅ No security vulnerabilities
- ✅ Ready to deploy or share

---

## 🔄 Decision-Making Framework

When uncertain, apply this priority order:

1. **User Safety & Security** (always first)
2. **Code Clarity** (for non-technical user learning)
3. **Working Functionality** (better 80% working than 0%)
4. **Performance** (if noticeable slowness exists)
5. **Code Elegance** (last priority)

Example: Security review blocks fancy feature → always choose security

---

## 💡 Failure Tolerance

**What's Acceptable**:
- Feature takes 2x estimated time (learning curve)
- Code gets refactored mid-project (understanding improves)
- Requirements clarified after phase start (normal in new projects)
- API changes from gdt.gov.vn (external dependency)

**What's Not Acceptable**:
- Credentials in code
- Unhandled errors (silent failures)
- Code that only developer understands
- Tests skipped to save time
- Documentation abandoned

---

## 🎓 Learning Outcomes Expected

By project completion, user should understand:
- ✅ How Python functions, loops, and data structures work
- ✅ How Flask routes work and request/response cycle
- ✅ How to make HTTP requests and handle responses
- ✅ How to test code and debug errors
- ✅ How to work with APIs and parse JSON/XML
- ✅ How to generate Excel files
- ✅ How authentication and sessions work
- ✅ Basic frontend (HTML/CSS/JavaScript)
- ✅ How to read and troubleshoot errors

---

## 📝 Amendment Log

| Date | Principle | Change | Rationale |
|------|-----------|--------|-----------|
| 2026-05-19 | Initial | Constitution created | Project kickoff |
|  |  |  |  |

---

**Approved By**: Huỳnh Anh Thuận  
**Date Approved**: 2026-05-19  
**Next Review**: After PLAYBOOK 3 (API Analysis)
