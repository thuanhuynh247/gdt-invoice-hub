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
            'US-690',
            'Core Registration Fee Calculation Engine',
            'normal',
            'planned',
            'docs/stories/US-690-rf-calculation.md',
            'Calculate registration fees for real estate (0.5%), motor vehicles (2%-12%), motorbikes (2%-5%), yachts/aircraft (1%) based on asset value and provincial rates under Decree 10/2022/NĐ-CP.'
        ),
        (
            'US-691',
            'RF Exemption Auditor',
            'normal',
            'planned',
            'docs/stories/US-691-rf-exemptions.md',
            'Audit registration fee exemptions for agricultural land, diplomatic assets, revolutionary merit family housing, and within-family agricultural transfers.'
        ),
        (
            'US-692',
            'Interactive Version 57 Compliance Hub UI and API',
            'normal',
            'planned',
            'docs/stories/US-692-v57-compliance-ui.md',
            'Provide a web dashboard at /v57-compliance-hub containing RF calculators, log lists, and REST JSON APIs.'
        ),
        (
            'US-693',
            'End-to-End V57 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-693-v57-test-suite.md',
            'Verify RF rates, provincial surcharges, exemptions, dashboard routes, and database logs.'
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
    print("V57 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
