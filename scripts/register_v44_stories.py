import sqlite3
import os

def register_v44_stories():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    stories = [
        (
            'US-560',
            'Decree 123 VAT Adjustments & Trade Discount Reconciliation Engine',
            'normal',
            'planned',
            'docs/stories/US-560-decree123-vat-adjustments.md',
            'Reconcile VAT adjustments, discounts, and replacement invoice logs against original invoices under Decree 123.'
        ),
        (
            'US-561',
            'Circular 67 & Circular 05 Science & Technology Development Fund Optimizer',
            'normal',
            'planned',
            'docs/stories/US-561-circular67-sci-tech-fund.md',
            'Optimize CIT allocation, model 5-year R&D expenditures qualified ratios, and audit unspent balances to prevent 20% CIT clawbacks.'
        ),
        (
            'US-562',
            'Interactive Version 44 Compliance Hub UI and API',
            'normal',
            'planned',
            'docs/stories/US-562-v44-compliance-ui.md',
            'Interactive bento grid console displaying real-time sliders for taxable income, allocation rate, qualified spend ratio, and welfare caps.'
        ),
        (
            'US-563',
            'End-to-End V44 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-563-v44-test-suite.md',
            'Comprehensive testing covering Decree 123 invoice links, Circular 67 clawback timelines, and web UI routes.'
        )
    ]
    
    for story in stories:
        cur.execute("""
            INSERT OR REPLACE INTO story (
                id, title, risk_lane, status, contract_doc, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, story)
        
    conn.commit()
    conn.close()
    print("V44 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_v44_stories()
