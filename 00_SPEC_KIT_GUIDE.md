# Spec-Kit Package: Invoice Download Webapp
## 🎯 How to Use This Specification Package

**Project Code**: INVOICE-WEBAPP-PLAN-A  
**Version**: 1.0  
**Created**: 2026-05-19  
**For**: Codex Development Environment

---

## 📋 What's in This Package?

You have **5 core spec documents** + **Master Prompt + Progress Tracker**. Together they form a **complete specification-driven development workflow**.

```
📦 SPEC-KIT PACKAGE
├── 01_constitution.md          ← Project governing principles
├── 02_specification.md         ← Functional requirements
├── 03_implementation_plan.md   ← Technical architecture
├── 04_tasks_breakdown.md       ← Actionable task list (THIS IS YOUR ROADMAP)
├── CODEX_MASTER_PROMPT.md      ← AI agent system prompt (load into Codex)
├── PROGRESS_TRACKER.md         ← Daily progress tracking
└── README (this file)          ← You are here
```

---

## 🚀 Getting Started in 5 Steps

### Step 1: Load Master Prompt into Codex (5 min)
```
1. Open CODEX_MASTER_PROMPT.md
2. Copy the XML section (from <role> to </guardrails>)
3. Go to your Codex chat
4. Paste into: Settings → Custom Instructions (or System Prompt)
5. Test: Ask Codex "Bắt đầu PLAYBOOK 1"
6. Codex should respond with full PLAYBOOK 1 guidance
```

**Expected**: Codex recognizes 7 playbooks and can guide you through setup

---

### Step 2: Read Constitution (10 min)
```
Why: Understand project values & principles
File: 01_constitution.md
Action: Read 10 principles, especially:
  - Principle 1: Pragmatic Over Perfect
  - Principle 2: Learning-First Mindset
  - Principle 5: Clear Communication
```

**Expected**: You understand "we value simplicity & clarity over fancy code"

---

### Step 3: Review Specification (15 min)
```
Why: Understand what you're building
File: 02_specification.md
Action: Read:
  - Executive Summary (1 min)
  - Core Features (6 features to implement)
  - User Stories (how real users use it)
```

**Expected**: You can describe the app to someone: "It downloads invoices from gdt.gov.vn"

---

### Step 4: Skim Implementation Plan (15 min)
```
Why: Understand technical approach
File: 03_implementation_plan.md
Action: Read:
  - Architecture Overview (tech stack)
  - Folder Structure
  - API Endpoints summary
```

**Expected**: You know "Backend is Python Flask, frontend is HTML/JS/Bootstrap"

---

### Step 5: Start with Task Breakdown (Now!)
```
Why: This is your actual roadmap
File: 04_tasks_breakdown.md
Action: 
  1. Read PHASE 1 fully (Tasks 1.1-1.2)
  2. Open Codex chat
  3. Ask: "Bắt đầu PLAYBOOK 1: ENVIRONMENT SETUP"
  4. Follow Codex guidance step-by-step
  5. Mark tasks ✅ as you complete them
```

**Expected**: You complete Task 1.1 (venv setup) and 1.2 (Flask skeleton) same day

---

## 📖 Reading Guide by Use Case

### "I'm completely new, where do I start?"
1. **Constitution** (01) - Understanding the mindset
2. **Specification** (02) - Understanding the goal
3. **Tasks** (04) - Do Task 1.1, ask Codex for help
4. **Master Prompt in Codex** - Load when ready to code

### "I just want to code, tell me what to do"
1. Load **Master Prompt** into Codex
2. Open **Tasks** (04)
3. Ask Codex: "What's next in PLAYBOOK 1?"
4. Execute task, ask when stuck

### "I'm stuck and don't understand what I'm building"
1. Reread **Specification** (02) section "Core Features"
2. Reread **Constitution** (01) principles
3. Ask Codex: "Giải thích feature X chi tiết hơn"

### "I want to understand the architecture"
1. Read **Implementation Plan** (03)
2. Look at "Folder Structure"
3. Look at "Module Responsibilities"
4. Ask Codex: "Explain module X"

---

## 🔄 The Spec-Driven Workflow

The **7 phases** in your master prompt directly map to these 4 spec documents:

```
PHASE 1-2: Setup & Learning
  → Guide: 01_constitution.md (principles)
  → Guide: CODEX_MASTER_PROMPT.md (PLAYBOOK 1-2)
  → Action: Tasks 1.1-2.3 in 04_tasks_breakdown.md

PHASE 3: API Analysis
  → Guide: 02_specification.md (user stories)
  → Guide: 03_implementation_plan.md (data model)
  → Action: Tasks 3.1-3.3 in 04_tasks_breakdown.md

PHASE 4-5: Backend & Frontend
  → Guide: 03_implementation_plan.md (routes, architecture)
  → Action: Tasks 4.1-5.3 in 04_tasks_breakdown.md

PHASE 6-7: Testing & Documentation
  → Guide: 01_constitution.md (quality standards)
  → Action: Tasks 6.1-7.3 in 04_tasks_breakdown.md
```

---

## 🎯 Key Concepts

### Constitution = "How We Build"
- 10 principles guiding decisions
- Example: "Simple > Fancy" (Principle 1)
- When stuck: "Does this follow the constitution?"

### Specification = "What We Build"
- 6 core features defined
- User stories showing real usage
- Acceptance criteria (how to test)
- When confused: "Is this feature in the spec?"

### Plan = "How It Works Technically"
- Architecture diagram
- Folder structure
- Module responsibilities
- API endpoints
- When coding: "Where does this code go?"

### Tasks = "Specific Steps"
- 21 tasks to complete
- Tests written first (Test-Driven)
- Checkpoints to verify progress
- When working: "What's the next task?"

---

## 💡 How Codex Helps

Once you load the **Master Prompt** into Codex, it becomes your development guide:

```
You: "Task 4.2 - tôi bắt đầu viết auth login route"
Codex: "Applying PLAYBOOK 4: BACKEND IMPLEMENTATION
  
  Task 4.2: Implement Auth Login Route
  Status: In Progress
  
  Here's what you need:
  1. Create auth/login.py with handle_login() function
  2. This function should:
     - Validate username/password not empty
     - Call gdt.gov.vn POST /login
     - Store session if successful
     - Return JSON {status, message}
  
  Here's starter code:
  [code provided]
  
  Next: Test your code with Task 4.2 tests
  Run: pytest tests/test_auth.py -v"
```

Codex becomes your:
- **Code generator** (writes starter code)
- **Debugger** (helps fix errors)
- **Teacher** (explains concepts)
- **Checker** (verifies you're on track)

---

## 📊 Progress Tracking

### How to Track Progress

1. **Daily**: Open `PROGRESS_TRACKER.md`
2. **Mark tasks**: Change ⬜ → 📝 → ✅
3. **Note blockers**: 🔴 BLOCKED if stuck
4. **Update status**: "Currently on PLAYBOOK X"
5. **End of day**: Save tracker

### Weekly Check-in
```
Week 1 Target:
  ✅ PLAYBOOK 1 (Setup) - 1 day
  📝 PLAYBOOK 2 (Learning) - 3-5 days
  = By end of week: Know Python + Flask basics

Week 2 Target:
  📝 PLAYBOOK 3 (API Analysis) - 5-7 days
  = By end of week: Know gdt.gov.vn API endpoints

Week 3 Target:
  📝 PLAYBOOK 4 (Backend) - 7-10 days
  = By end of week: All routes working (login, search, download, export)

Week 4 Target:
  📝 PLAYBOOK 5 (Frontend) - 3-5 days
  📝 PLAYBOOK 6 (Testing) - 3-5 days
  = By end of week: Full app working

Week 5 Target:
  📝 PLAYBOOK 7 (Documentation) - 2 days
  = Finish: App ready to share
```

---

## 🚨 When You Get Stuck

### Scenario 1: "I don't understand Python concepts"
**Solution**: 
1. Go back to PLAYBOOK 2 in master prompt
2. Ask Codex: "Python là cái gì? Giải thích chi tiết"
3. Request code examples
4. Practice with small scripts

### Scenario 2: "I don't know what gdt.gov.vn API returns"
**Solution**:
1. Go back to PLAYBOOK 3 in master prompt
2. Open Chrome DevTools (F12)
3. Login to gdt.gov.vn
4. Capture API requests in Network tab
5. Ask Codex: "Analyze this response and tell me the fields"

### Scenario 3: "My code has bugs"
**Solution**:
1. Paste error message to Codex
2. Ask: "Lỗi này là gì? Fix thế nào?"
3. Follow Codex debugging guidance
4. Check PLAYBOOK 6 (Testing & Debugging) section

### Scenario 4: "I'm not sure which task to do next"
**Solution**:
1. Look at 04_tasks_breakdown.md
2. Find your current status
3. Next task is marked [P] or [T] or just next number
4. Ask Codex: "Cho tôi PLAYBOOK cho task tiếp theo"

---

## 📝 Document Maintenance

### When to Update Constitution
- IF: Project principles change
- THEN: Update 01_constitution.md
- Example: "We decided to use database → update Principle 10"

### When to Update Specification
- IF: Requirements change
- THEN: Update 02_specification.md
- Example: "User wants PDF export → add to Feature X"

### When to Update Plan
- IF: Architecture changes
- THEN: Update 03_implementation_plan.md
- Example: "Found new gdt.gov.vn endpoint → update API section"

### When to Update Tasks
- IF: Task proves harder/easier than expected
- THEN: Update duration in 04_tasks_breakdown.md
- Example: "Task 3.1 took 5 hours not 2 → update time estimate"

---

## ✅ Quality Gates

**Before moving to next PLAYBOOK**, verify:

```
GATE 1: Working Code
  ✅ Can run Flask app
  ✅ No import errors
  ✅ Can access localhost:5000

GATE 2: Tests Passing
  ✅ Run: pytest
  ✅ All tests pass
  ✅ Coverage ≥70%

GATE 3: Manual Testing
  ✅ User scenario works end-to-end
  ✅ Errors show friendly messages
  ✅ No blank screens or crashes

GATE 4: Code Quality
  ✅ Docstrings on all functions
  ✅ No commented-out code
  ✅ No hardcoded credentials

GATE 5: Understanding
  ✅ You can explain what code does
  ✅ You know WHY it's structured this way
  ✅ You could modify it if needed
```

---

## 🎓 Learning Outcomes

By completing all 7 playbooks, you'll understand:

### Python
- ✅ Functions, loops, dictionaries, lists
- ✅ File I/O, JSON/XML parsing
- ✅ Virtual environments & pip
- ✅ Testing with pytest

### Flask
- ✅ Routing (@app.route)
- ✅ Request/response handling
- ✅ Session management
- ✅ Error handling

### Web Development
- ✅ HTML5 templates
- ✅ CSS styling (Bootstrap)
- ✅ JavaScript (fetch API, DOM)
- ✅ HTTP methods (GET, POST)

### APIs
- ✅ HTTP requests with requests library
- ✅ JSON/XML parsing
- ✅ Error handling
- ✅ Authentication & sessions

### Excel
- ✅ Creating Excel files with openpyxl
- ✅ Formatting cells, colors, fonts
- ✅ Data export

### DevOps / Deployment
- ✅ Local development setup
- ✅ Virtual environment management
- ✅ Logging & debugging
- ✅ Git basics (implied)

---

## 📚 Quick Reference

| Need | File | Section |
|------|------|---------|
| Project principles | 01_constitution.md | PRINCIPLE 1-10 |
| What to build | 02_specification.md | Core Features |
| How it works technically | 03_implementation_plan.md | Architecture |
| What to do right now | 04_tasks_breakdown.md | PHASE 1 |
| Stuck on code? | CODEX_MASTER_PROMPT.md | PLAYBOOK 6 |
| Tracking progress | PROGRESS_TRACKER.md | Playbook Checklist |

---

## 🎉 Success Indicator

You'll know you're successful when:

1. **Week 1 end**: Can explain "why we chose Flask over Django"
2. **Week 2 end**: Can reverse-engineer an API using Chrome DevTools
3. **Week 3 end**: Can write Python functions and Flask routes
4. **Week 4 end**: Can build a working web app end-to-end
5. **Week 5 end**: Have a professional app you could show to others

---

## 🔗 Next Steps

1. **RIGHT NOW**: 
   - Read this file completely ✓
   - Read 01_constitution.md (10 min)
   - Read 02_specification.md (15 min)

2. **NEXT 30 MIN**:
   - Load master prompt into Codex
   - Ask Codex for PLAYBOOK 1 guidance
   - Start Task 1.1 (environment setup)

3. **TODAY**:
   - Complete Task 1.1 (venv setup)
   - Complete Task 1.2 (Flask skeleton)
   - Run Flask app successfully
   - Update PROGRESS_TRACKER.md

4. **THIS WEEK**:
   - Complete PLAYBOOK 1-2 (Setup & Learning)
   - Update progress tracker daily
   - Don't move to PLAYBOOK 3 until you understand Python/Flask

5. **ONGOING**:
   - Follow 4_tasks_breakdown.md sequentially
   - Ask Codex when stuck
   - Update PROGRESS_TRACKER.md each session
   - Celebrate each completed PLAYBOOK! 🎊

---

## 💬 Questions?

When uncertain, ask Codex:

```
"Tôi không hiểu [concept]. Giải thích chi tiết với ví dụ"
"Task [X] là gì? Tôi phải làm gì?"
"Làm sao test code này?"
"Lỗi [error] là gì?"
"Tiếp theo tôi phải làm gì?"
```

---

**Spec-Kit Version**: 1.0  
**Last Updated**: 2026-05-19  
**Status**: ✅ Ready to Use

**Your Next Step**: Load Master Prompt into Codex, then ask for PLAYBOOK 1 guidance. 🚀
