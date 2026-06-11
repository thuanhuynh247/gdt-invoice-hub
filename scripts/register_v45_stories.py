import sqlite3
import os

def register_v45_stories():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    stories = [
        (
            'US-570',
            'Circular 80 Preferential CIT Rates & Tax Holidays Optimizer',
            'normal',
            'planned',
            'docs/stories/US-570-preferential-cit-rates.md',
            'Calculate preferential CIT rates (10%, 15%, 17%) and model tax exemption and reduction holidays.'
        ),
        (
            'US-571',
            'Decree 132 Transfer Pricing Safe Harbor & APA Auditor Engine',
            'normal',
            'planned',
            'docs/stories/US-571-tp-safe-harbors.md',
            'Evaluate Safe Harbor eligibility (revenue < 50B VND, net margins) and log APA compliance terms.'
        ),
        (
            'US-572',
            'Interactive Version 45 Compliance Hub UI and API',
            'normal',
            'planned',
            'docs/stories/US-572-v45-compliance-ui.md',
            'Webpage dashboard console at /v45-compliance-hub showing CIT incentives, TP Safe Harbor results, and dynamic simulations.'
        ),
        (
            'US-573',
            'End-to-End V45 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-573-v45-test-suite.md',
            'Comprehensive testing covering CIT incentives, tax holidays allocation, TP Safe Harbor logic, and API routes.'
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
    print("V45 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_v45_stories()
