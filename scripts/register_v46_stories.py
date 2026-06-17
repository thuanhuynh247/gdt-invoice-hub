import sqlite3
import os

def register_v46_stories():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    stories = [
        (
            'US-580',
            'Decree 123 E-Invoice Error Alerts & Form 04/SS-HĐĐT Status Tracker',
            'normal',
            'planned',
            'docs/stories/US-580-e-invoice-incidents.md',
            'Parse GDT Form 04/SS-HĐĐT logs, track error response statuses (Accepted, Rejected, Pending), and raise warnings for late submissions.'
        ),
        (
            'US-581',
            'Circular 78 Legacy Conversions & Double-Deduction Auditing Engine',
            'normal',
            'planned',
            'docs/stories/US-581-invoice-conversion-reconciliation.md',
            'Track converted e-invoices print logs, match XML invoices with paper tickets, and prevent duplicate expense claims.'
        ),
        (
            'US-582',
            'Interactive Version 46 Compliance Hub UI and API',
            'normal',
            'planned',
            'docs/stories/US-582-v46-compliance-ui.md',
            'Webpage dashboard console at /v46-compliance-hub displaying Form 04/SS log timelines, conversion alerts, and simulation API routes.'
        ),
        (
            'US-583',
            'End-to-End V46 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-583-v46-test-suite.md',
            'Comprehensive testing covering Decree 123 error logs, Form 04/SS submission deadlines, conversion double claims auditing, and endpoints.'
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
    print("V46 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_v46_stories()
