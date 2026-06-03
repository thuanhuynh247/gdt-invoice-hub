# 🚀 CODEX WORKSPACE CHAT PROMPT
**Copy-paste this into Codex chat to run specs sequentially**

---

## PASTE THIS INTO CODEX CHAT (Just once, at beginning)

```
Hôm nay tôi muốn xây dựng Invoice Download Webapp theo spec-kit workflow.

Tôi có 5 specification documents:
1. 01_constitution.md - 10 nguyên tắc project
2. 02_specification.md - 6 features, 4 user stories
3. 03_implementation_plan.md - Architecture, API design
4. 04_tasks_breakdown.md - 21 tasks cụ thể

Workflow của tôi:
- PLAYBOOK 1-2 (Week 1): Setup + Learn Python/Flask
- PLAYBOOK 3 (Week 2): API Analysis  
- PLAYBOOK 4 (Week 3): Backend Implementation
- PLAYBOOK 5 (Week 4): Frontend
- PLAYBOOK 6-7 (Week 5): Testing + Documentation

Giờ tôi muốn bắt đầu PLAYBOOK 1. Hướng dẫn tôi từng bước cụ thể:
- Task là gì?
- Tôi phải làm gì?
- Code ví dụ nếu cần
- Cách verify khi xong
- Task tiếp theo là gì?

Khi tôi hỏi "Next" hoặc "Status" hoặc tên task cụ thể, bạn auto-guide.
```

---

## THEN USE THESE SIMPLE COMMANDS IN CHAT

### **Navigation Commands**
```
"Task 1.1" → Codex shows Task 1.1 guidance
"Next" → Codex suggests next task
"Status" → Codex shows current progress
"PLAYBOOK 2" → Jump to PLAYBOOK 2
```

### **Help Commands**
```
"Explain [concept]" → Deep dive on concept
"Code" → Generate code for current task
"Test" → How to test current task
"Stuck: [error]" → Debug the error
```

### **Tracking Commands**
```
"Done" → Mark task complete, move to next
"Daily report" → Summary of today's progress
"Check progress" → Show overall completion %
```

---

## EXAMPLE CONVERSATION

```
You: [Paste the prompt above]

Codex: ✅ Understood! You're doing Spec-Driven Development for Invoice Webapp.

📊 PROJECT STATE
Current Phase: PLAYBOOK 1 (Environment Setup)
Current Task: 1.1 - Virtual Environment
Progress: 0/21 tasks

Let's start PLAYBOOK 1, Task 1.1:

TASK 1.1: ENVIRONMENT SETUP
Duration: 30 min
What: Create Python virtual environment + install packages

STEP 1: Create folder
$ mkdir invoice-webapp && cd invoice-webapp

STEP 2: Create venv
$ python -m venv venv

STEP 3: Activate
$ source venv/bin/activate  # Mac/Linux
$ venv\Scripts\activate     # Windows

STEP 4: Install packages
$ pip install Flask requests selenium openpyxl pytest

STEP 5: Verify Flask
$ python -c "import flask; print(flask.__version__)"

When done, ask: "Task 1.1 done" → I'll guide 1.2

═══════════════════════════════════════════════════════════

You: Done! Flask 2.3.3 installed

Codex: ✅ Great! CHECKPOINT: Environment ready
Next: Task 1.2 - Create Flask skeleton

TASK 1.2: FLASK SKELETON APP
Duration: 45 min

Create app.py:
[Full code provided]

When done, ask: "Task 1.2 done" → I'll guide PLAYBOOK 2

═══════════════════════════════════════════════════════════

You: Done, python app.py works!

Codex: ✅ CHECKPOINT 1 PASSED: Flask app runs on localhost:5000

📊 PROGRESS: 2/21 tasks (10%)

PLAYBOOK 1 COMPLETE ✅

Ready for PLAYBOOK 2 (Python + Flask learning)?
Ask: "PLAYBOOK 2"

═══════════════════════════════════════════════════════════

You: PLAYBOOK 2

Codex: Starting PLAYBOOK 2: Python + Flask Learning (Days 2-5)

Duration: 3-5 days
Tasks: 2.1, 2.2, 2.3

TASK 2.1: PYTHON BASICS
Learn: Variables, functions, loops, dictionaries

Exercise: Write a Python script that:
- Creates a dictionary of invoices
- Loops through them
- Prints each invoice

[Code example provided]

When done, ask: "Task 2.1 done"
```

---

## 🎯 WHY THIS WORKS

✅ **Simple**: Just paste once, then use 1-word commands  
✅ **Conversational**: Feels natural in chat  
✅ **Focused**: Codex tracks your progress  
✅ **Flexible**: Can jump tasks or ask questions anytime  
✅ **No System Prompts**: Just regular chat interaction  

---

## 📋 QUICK REFERENCE

| You Type | Codex Does |
|----------|-----------|
| "Next" | Shows next task |
| "Status" | Shows progress % |
| "Done" | Marks complete, suggests next |
| "Explain X" | Deep dive on concept |
| "Code" | Generates code |
| "Stuck: [error]" | Debug help |
| "Task 3.1" | Jump to specific task |
| "PLAYBOOK 4" | Jump to phase |

---

## 🚀 START NOW

1. **Copy the prompt above** (entire block starting with "Hôm nay tôi...")
2. **Paste into Codex chat**
3. **Done!** Codex will guide you through all 21 tasks

That's it. No system prompts, no complex setup. Just chat.

---

**Version**: 1.0  
**Status**: Ready to use  
**Next**: Paste into Codex, then ask "Next"
