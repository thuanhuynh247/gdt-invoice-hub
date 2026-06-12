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
        # V60: Agricultural Land Use Tax (ALUT)
        ('US-720', 'Core Agricultural Land Use Tax Calculation Engine', 'normal', 'planned',
         'docs/stories/US-720-alut-calculation.md',
         'Calculate ALUT based on land grade (1 to 6) and crop type (annual vs perennial crops) under Law on Agricultural Land Use Tax 1993 in paddy rice equivalent per hectare.'),
        ('US-721', 'ALUT Exemption Auditor', 'normal', 'planned',
         'docs/stories/US-721-alut-exemptions.md',
         'Audit ALUT exemptions for household agricultural production, agricultural cooperatives, and research farms under Resolution 117/2020/QH14.'),
        ('US-722', 'Interactive Version 60 Compliance Hub UI and API', 'normal', 'planned',
         'docs/stories/US-722-v60-compliance-ui.md',
         'Provide a web dashboard at /v60-compliance-hub with ALUT calculators and REST APIs.'),
        ('US-723', 'End-to-End V60 Verification Test Suite', 'normal', 'planned',
         'docs/stories/US-723-v60-test-suite.md',
         'Verify ALUT calculations, exemptions, and API routes.'),

        # V61: Environment Protection Fee for Wastewater (EPFW)
        ('US-730', 'Environment Protection Fee for Wastewater Engine', 'normal', 'planned',
         'docs/stories/US-730-epfw-calculation.md',
         'Calculate EPFW for domestic wastewater (10% of clean water price) and industrial wastewater (1,500,000 VND flat base + variable heavy-metal pollution factors: COD, TSS, Pb, Cd, Hg) under Decree 53/2020/NĐ-CP.'),
        ('US-731', 'EPFW Exemption Auditor', 'normal', 'planned',
         'docs/stories/US-731-epfw-exemptions.md',
         'Audit EPFW exemptions for cooling water, natural runoff water, agricultural supply, and rural domestic water.'),
        ('US-732', 'Interactive Version 61 Compliance Hub UI and API', 'normal', 'planned',
         'docs/stories/US-732-v61-compliance-ui.md',
         'Provide a web dashboard at /v61-compliance-hub with EPFW calculators and REST APIs.'),
        ('US-733', 'End-to-End V61 Verification Test Suite', 'normal', 'planned',
         'docs/stories/US-733-v61-test-suite.md',
         'Verify EPFW calculations, industrial variable fees, exemptions, and API routes.')
    ]

    for story in stories:
        cur.execute("INSERT OR REPLACE INTO story (id, title, risk_lane, status, contract_doc, notes) VALUES (?, ?, ?, ?, ?, ?)", story)

    conn.commit()
    conn.close()
    print("V60 & V61 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
