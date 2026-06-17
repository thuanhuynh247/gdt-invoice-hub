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
            'US-660',
            'Core Natural Resources Tax Calculation Engine',
            'normal',
            'planned',
            'docs/stories/US-660-nrt-calculation.md',
            'Classify and calculate NRT on minerals, water, timber, and marine products using ad-valorem rates.'
        ),
        (
            'US-661',
            'NRT Exemption & Threshold Auditor',
            'normal',
            'planned',
            'docs/stories/US-661-nrt-exemptions.md',
            'Audit exemptions for agricultural water, small-scale hydropower (<=2MW), and self-consumed resources.'
        ),
        (
            'US-662',
            'Interactive Version 54 Compliance Hub UI and API',
            'normal',
            'planned',
            'docs/stories/US-662-v54-compliance-ui.md',
            'Provide a web dashboard at /v54-compliance-hub containing NRT calculators, logs, and REST JSON APIs.'
        ),
        (
            'US-663',
            'End-to-End V54 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-663-v54-test-suite.md',
            'Verify NRT rates, agricultural exemptions, hydropower thresholds, dashboard routes, and database logs.'
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
    print("V54 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
