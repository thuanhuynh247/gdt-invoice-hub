import sqlite3
import os

def register_stories():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    stories = [
        (
            'US-670',
            'Core Import-Export Tax Calculation Engine',
            'normal',
            'planned',
            'docs/stories/US-670-iet-calculation.md',
            'Calculate import duties (preferential MFN, ordinary, FTA) and export duties on cargo under Law 107/2016/QH13.'
        ),
        (
            'US-671',
            'IET Exemption & Threshold Auditor',
            'normal',
            'planned',
            'docs/stories/US-671-iet-exemptions.md',
            'Audit exemptions for processing contracts, temporary imports/re-exports, and low-value gifts (<= 2,000,000 VND).'
        ),
        (
            'US-672',
            'Interactive Version 55 Compliance Hub UI and API',
            'normal',
            'planned',
            'docs/stories/US-672-v55-compliance-ui.md',
            'Provide a web dashboard at /v55-compliance-hub containing IET calculators, logs, and REST JSON APIs.'
        ),
        (
            'US-673',
            'End-to-End V55 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-673-v55-test-suite.md',
            'Verify IET rates, processing exemptions, low-value gift thresholds, dashboard routes, and database logs.'
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
    print("V55 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
