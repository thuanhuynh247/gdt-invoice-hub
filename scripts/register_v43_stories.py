import sqlite3
import os

def register_v43_stories():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    stories = [
        (
            'US-550',
            'IAS 12 Deferred Tax Automation Ledger & Temporary Difference Engine',
            'normal',
            'planned',
            'docs/stories/US-550-ias12-deferred-tax.md',
            'Ingest carrying amounts and tax bases, calculate temporary differences, and compute/save deferred tax assets and liabilities under IAS 12.'
        ),
        (
            'US-551',
            'IFRS 15 Revenue Recognition & Contract Milestone Matcher',
            'normal',
            'planned',
            'docs/stories/US-551-ifrs15-revenue.md',
            'Reconcile invoices against contract milestones, allocate transaction prices using standalone selling prices, defer unearned revenue, and generate revenue schedules.'
        ),
        (
            'US-552',
            'IFRS 16 Lease Amortization Matcher & ROU schedule generator',
            'normal',
            'planned',
            'docs/stories/US-552-ifrs16-leases.md',
            'Amortize right-of-use assets and lease liabilities month-by-month and calculate interest/principal schedules under IFRS 16.'
        ),
        (
            'US-553',
            'OECD Pillar Two Global Minimum Tax (GMT) Estimator',
            'normal',
            'planned',
            'docs/stories/US-553-pillar-two.md',
            'Consolidate group-wide ETR across multiple tenant profiles (MSTs) and estimate Pillar Two minimum tax liability.'
        ),
        (
            'US-554',
            'Interactive IFRS Translation & OECD GMT Compliance Dashboard UI',
            'normal',
            'planned',
            'docs/stories/US-554-ifrs-dashboard.md',
            'Interactive dashboard page at /v43-ifrs-dashboard featuring bento-grid widgets, dynamic sliders, group ETR maps, and advisor debate summaries.'
        ),
        (
            'US-555',
            'End-to-End V43 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-555-v43-test-suite.md',
            'Comprehensive testing covering IAS 12 computations, IFRS 15 revenue allocations, IFRS 16 amortization tables, Pillar Two estimations, and dashboard routes.'
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
    print("V43 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_v43_stories()
