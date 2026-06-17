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
        ('US-710', 'Core Non-Agricultural Land Use Tax Engine', 'normal', 'planned',
         'docs/stories/US-710-nalut-calculation.md',
         'Calculate NALUT for residential (tiered 0.03%-0.15%), commercial (0.03%), production (0.03%), and idle land (surcharge) under Law 48/2010/QH12.'),
        ('US-711', 'NALUT Exemption Auditor', 'normal', 'planned',
         'docs/stories/US-711-nalut-exemptions.md',
         'Audit NALUT exemptions for public welfare, religious, and diplomatic land uses.'),
        ('US-712', 'Interactive Version 59 Compliance Hub UI and API', 'normal', 'planned',
         'docs/stories/US-712-v59-compliance-ui.md',
         'Provide a web dashboard at /v59-compliance-hub with NALUT calculators and REST APIs.'),
        ('US-713', 'End-to-End V59 Verification Test Suite', 'normal', 'planned',
         'docs/stories/US-713-v59-test-suite.md',
         'Verify NALUT tiered rates, idle surcharge, exemptions, and API endpoints.'),
    ]

    for story in stories:
        cur.execute("INSERT OR REPLACE INTO story (id, title, risk_lane, status, contract_doc, notes) VALUES (?, ?, ?, ?, ?, ?)", story)

    conn.commit()
    conn.close()
    print("V59 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
