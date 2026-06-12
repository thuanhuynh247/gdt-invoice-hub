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
            'US-680',
            'Core License Fee Calculation Engine',
            'normal',
            'planned',
            'docs/stories/US-680-lf-calculation.md',
            'Calculate annual license fees for enterprises and households based on charter capital and revenue brackets under Decree 139/2016/NĐ-CP.'
        ),
        (
            'US-681',
            'LF Exemption Auditor',
            'normal',
            'planned',
            'docs/stories/US-681-lf-exemptions.md',
            'Audit exemptions for households with low revenue (<= 100M VND/year), newly established first-year entities, and agricultural cooperatives.'
        ),
        (
            'US-682',
            'Interactive Version 56 Compliance Hub UI and API',
            'normal',
            'planned',
            'docs/stories/US-682-v56-compliance-ui.md',
            'Provide a web dashboard at /v56-compliance-hub containing LF calculators, log lists, and REST JSON APIs.'
        ),
        (
            'US-683',
            'End-to-End V56 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-683-v56-test-suite.md',
            'Verify LF rates, branch aggregations, exemptions, dashboard routes, and database logs.'
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
    print("V56 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
