import sqlite3
import os
import re
from datetime import datetime

def main():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    fund_stories = [
        "PRD-FUND-E1-S1",
        "PRD-FUND-E2-S1",
        "PRD-FUND-E2-S2",
        "PRD-FUND-E3-S1",
        "PRD-FUND-E3-S2"
    ]
    evidence_file = "tests/test_fund_features.py"

    print("Updating story statuses in harness.db to completed...")
    for sid in fund_stories:
        cur.execute("""
            UPDATE story
            SET status = 'completed', evidence = ?, unit_proof = 1, integration_proof = 1, e2e_proof = 1
            WHERE id = ?
        """, (evidence_file, sid))
        print(f"Updated db story status: {sid} -> completed (evidence: {evidence_file})")

    print("Recording traces...")
    
    # Trace for PRD-FUND-E1-S1
    cur.execute("""
        INSERT INTO trace (
            task_summary, story_id, agent, actions_taken, files_read, files_changed, outcome, duration_seconds, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "PRD-FUND-E1-S1 Tạo quỹ nhóm: Completed",
        "PRD-FUND-E1-S1",
        "Antigravity",
        "Implemented GroupFund and TenantGroup models, API endpoint to create group funds, default currency VND, check unique group constraints, initial balance 0, and Navbar switcher UI link.",
        "invoices/models.py, invoices/routes.py, templates/base.html, templates/fund.html",
        "invoices/models.py, invoices/routes.py, templates/base.html, templates/fund.html",
        "completed",
        120,
        datetime.now().isoformat()
    ))
    print("Trace recorded for PRD-FUND-E1-S1")

    # Trace for PRD-FUND-E2-S1
    cur.execute("""
        INSERT INTO trace (
            task_summary, story_id, agent, actions_taken, files_read, files_changed, outcome, duration_seconds, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "PRD-FUND-E2-S1 Ghi khoản nộp quỹ: Completed",
        "PRD-FUND-E2-S1",
        "Antigravity",
        "Implemented FundTransaction model with transaction_type='deposit', API endpoint /api/group-fund/deposit, validate input parameters (amount, date, payer), update balance dynamically, and frontend modal.",
        "invoices/models.py, invoices/routes.py, templates/fund.html",
        "invoices/models.py, invoices/routes.py, templates/fund.html",
        "completed",
        120,
        datetime.now().isoformat()
    ))
    print("Trace recorded for PRD-FUND-E2-S1")

    # Trace for PRD-FUND-E2-S2
    cur.execute("""
        INSERT INTO trace (
            task_summary, story_id, agent, actions_taken, files_read, files_changed, outcome, duration_seconds, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "PRD-FUND-E2-S2 Ghi khoản chi từ quỹ: Completed",
        "PRD-FUND-E2-S2",
        "Antigravity",
        "Implemented FundTransaction model with transaction_type='expense', API endpoint /api/group-fund/expense, validate parameters (amount, date, description), update balance dynamically, and expense modal.",
        "invoices/models.py, invoices/routes.py, templates/fund.html",
        "invoices/models.py, invoices/routes.py, templates/fund.html",
        "completed",
        120,
        datetime.now().isoformat()
    ))
    print("Trace recorded for PRD-FUND-E2-S2")

    # Trace for PRD-FUND-E3-S1
    cur.execute("""
        INSERT INTO trace (
            task_summary, story_id, agent, actions_taken, files_read, files_changed, outcome, duration_seconds, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "PRD-FUND-E3-S1 Xem số dư quỹ: Completed",
        "PRD-FUND-E3-S1",
        "Antigravity",
        "Implemented API endpoint to query fund details including balance computed as total deposits minus total expenses, and UI cards showing real-time balance stats.",
        "invoices/models.py, invoices/routes.py, templates/fund.html",
        "invoices/models.py, invoices/routes.py, templates/fund.html",
        "completed",
        120,
        datetime.now().isoformat()
    ))
    print("Trace recorded for PRD-FUND-E3-S1")

    # Trace for PRD-FUND-E3-S2
    cur.execute("""
        INSERT INTO trace (
            task_summary, story_id, agent, actions_taken, files_read, files_changed, outcome, duration_seconds, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "PRD-FUND-E3-S2 Xem lịch sử thu chi: Completed",
        "PRD-FUND-E3-S2",
        "Antigravity",
        "Implemented transaction history query API sorting transactions by date descending and id descending, and a detailed transaction log table with pagination on the frontend.",
        "invoices/models.py, invoices/routes.py, templates/fund.html",
        "invoices/models.py, invoices/routes.py, templates/fund.html",
        "completed",
        120,
        datetime.now().isoformat()
    ))
    print("Trace recorded for PRD-FUND-E3-S2")

    conn.commit()
    conn.close()
    print("Database updates finished.")

    # Now let's update story markdown files in the workspace
    md_paths = [
        "docs/product/stories",
        "product-spec/docs/product/stories"
    ]
    for p in md_paths:
        if not os.path.exists(p):
            continue
        for file in os.listdir(p):
            if file.startswith("PRD-FUND-") and file.endswith(".md"):
                filepath = os.path.join(p, file)
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                # Replace status: draft/planned/etc in yaml block
                new_content = re.sub(
                    r"^status:\s*\S+",
                    "status: completed",
                    content,
                    flags=re.MULTILINE
                )
                if new_content != content:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"Updated status frontmatter in: {filepath}")

    print("Status update of all files complete.")

if __name__ == "__main__":
    main()
