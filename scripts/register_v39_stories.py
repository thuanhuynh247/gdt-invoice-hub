import sqlite3
import os

def register_v39_stories():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    stories = [
        (
            'US-510',
            'Vietnamese Deferred Income Tax (VAS 17) Calculation Engine',
            'normal',
            'planned',
            'docs/stories/US-510-vas17-engine.md',
            'Compute accounting profit vs taxable income differences and deferred tax assets/liabilities under VAS 17.'
        ),
        (
            'US-511',
            'VAS 17 Deferred Tax Advisory Panel & Journal Entry Scaffolder',
            'normal',
            'planned',
            'docs/stories/US-511-vas17-journal.md',
            'Provide double-entry bookkeeping suggestions and deferred tax advisor summary cards.'
        ),
        (
            'US-512',
            'Cash-Flow Sensitivity Stress Simulator & Runway Gauge',
            'normal',
            'planned',
            'docs/stories/US-512-cash-stress.md',
            'Interactive A/R and A/P collection sliders projecting runway months with animated SVG circular gauge.'
        ),
        (
            'US-513',
            'Supplier Multi-Dimensional Risk Scorecard & SVG Network Graph',
            'normal',
            'planned',
            'docs/stories/US-513-supplier-risk-graph.md',
            'Render zero-dependency SVG transaction network highlighting high-risk supplier nodes.'
        ),
        (
            'US-514',
            'Live GDT High-Risk Supplier Scraper Simulator & Offcanvas Auditor',
            'normal',
            'planned',
            'docs/stories/US-514-gdt-scraper-sim.md',
            'Audit panel and offcanvas drawer checking partner tax status against GDT blacklist databases.'
        ),
        (
            'US-515',
            'End-to-End V39 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-515-v39-test-suite.md',
            'Comprehensive validation testing covering VAS 17 tax differences, cash flow stress sandbox, and supplier risk network.'
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
    print("V39 stories successfully registered/updated in harness.db")

if __name__ == "__main__":
    register_v39_stories()
