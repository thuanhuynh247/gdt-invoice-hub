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
            'US-700',
            'Core Natural Resources Tax Calculation Engine',
            'normal',
            'planned',
            'docs/stories/US-700-nrt-calculation.md',
            'Calculate NRT for metallic minerals (7%-25%), non-metallic minerals (5%-15%), crude oil (6%-10%), natural gas (2%), coal (5%-7%), water (3%), timber (15%-25%), marine (2%) under Law 45/2009/QH12.'
        ),
        (
            'US-701',
            'NRT Exemption Auditor',
            'normal',
            'planned',
            'docs/stories/US-701-nrt-exemptions.md',
            'Audit NRT exemptions for agricultural/aquaculture water, hydroelectric water, and national defense resource extraction.'
        ),
        (
            'US-702',
            'Interactive Version 58 Compliance Hub UI and API',
            'normal',
            'planned',
            'docs/stories/US-702-v58-compliance-ui.md',
            'Provide a web dashboard at /v58-compliance-hub containing NRT calculators, log lists, and REST JSON APIs.'
        ),
        (
            'US-703',
            'End-to-End V58 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-703-v58-test-suite.md',
            'Verify NRT rates, resource categories, exemptions, dashboard routes, and database logs.'
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
    print("V58 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
