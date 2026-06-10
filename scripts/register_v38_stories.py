import sqlite3
import os

def register_v38_stories():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    stories = [
        (
            'US-500',
            'Electronic Delivery Note (PXK) Parser & Matcher Engine',
            'normal',
            'planned',
            'docs/stories/US-500-pxk-parser.md',
            'Parse GDT XML delivery notes and match them to subsequent commercial invoices based on contract and item details.'
        ),
        (
            'US-501',
            'Reconciliation & Timing Penalty Advisor',
            'normal',
            'planned',
            'docs/stories/US-501-timing-penalty.md',
            'Track delay between delivery note date and commercial invoice date, alerting on administrative fines or CIT deductibility risk.'
        ),
        (
            'US-502',
            'Interactive Reconciliation Timeline Dashboard',
            'normal',
            'planned',
            'docs/stories/US-502-reconciliation-dashboard.md',
            'Provide a glassmorphic dashboard tracking delivery notes status and visual Gantt-like timeline of invoice matching.'
        ),
        (
            'US-503',
            'AI Logistics Cost Allocation Engine (VAS 02)',
            'normal',
            'planned',
            'docs/stories/US-503-logistics-allocation.md',
            'Analyze logistics, freight, and shipping invoices to auto-allocate transport costs to purchase invoices.'
        ),
        (
            'US-504',
            'Inventory Cost-Base Adjusted Valuation Report',
            'normal',
            'planned',
            'docs/stories/US-504-inventory-valuation.md',
            'Generate adjusted cost base inventory valuation reports integrating allocated logistics costs under VAS 02 rules.'
        ),
        (
            'US-505',
            'End-to-End V38 Validation Test Suite',
            'normal',
            'planned',
            'docs/stories/US-505-v38-test-suite.md',
            'Comprehensive pytest coverage for electronic delivery notes parser, reconciliation timeline, logistics allocator, and cost-base adjuster.'
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
    print("V38 stories successfully registered/updated in harness.db")

if __name__ == "__main__":
    register_v38_stories()
