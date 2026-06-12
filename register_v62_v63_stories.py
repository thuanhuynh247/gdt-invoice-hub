import sqlite3
import datetime

def main():
    conn = sqlite3.connect("harness.db")
    c = conn.cursor()
    
    stories = [
        # V62
        (
            'US-740',
            'Core Environment Protection Fee for Emissions Engine',
            'normal',
            'docs/stories/US-740-epfe-calculation.md',
            'completed',
            'Calculate EPFE fixed charges (3,000,000 VND/year) and variable loads for dust (0.8 VND/kg), SOx (0.7 VND/kg), NOx (0.8 VND/kg), and CO (0.5 VND/kg) under Decree 153/2024/NĐ-CP.',
            1, 1, 1, 0,
            'tests/test_v62_features.py'
        ),
        (
            'US-741',
            'EPFE Exemption Auditor',
            'normal',
            'docs/stories/US-741-epfe-exemptions.md',
            'completed',
            'Verify exemptions for out-of-scope small businesses and zero-emission certified operations.',
            1, 1, 1, 0,
            'tests/test_v62_features.py'
        ),
        (
            'US-742',
            'Interactive Version 62 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-742-v62-compliance-ui.md',
            'completed',
            'Provide a web dashboard at /v62-compliance-hub with EPFE calculators and REST APIs.',
            1, 1, 1, 0,
            'tests/test_v62_features.py'
        ),
        (
            'US-743',
            'End-to-End V62 Verification Test Suite',
            'normal',
            'docs/stories/US-743-v62-test-suite.md',
            'completed',
            'Verify EPFE calculations, variable pollutant loads, exemptions, and API endpoints.',
            1, 1, 1, 0,
            'tests/test_v62_features.py'
        ),
        # V63
        (
            'US-750',
            'Core Environment Protection Fee for Mineral Extraction Engine',
            'normal',
            'docs/stories/US-750-epfme-calculation.md',
            'completed',
            'Calculate EPFME for crude oil, natural gas, associated gas, stone, and clay, and apply 60% salvage discount under Decree 27/2023/NĐ-CP.',
            1, 1, 1, 0,
            'tests/test_v63_features.py'
        ),
        (
            'US-751',
            'EPFME Exemption Auditor',
            'normal',
            'docs/stories/US-751-epfme-exemptions.md',
            'completed',
            'Verify exemptions for household building, security/disaster relief, and site reclamation.',
            1, 1, 1, 0,
            'tests/test_v63_features.py'
        ),
        (
            'US-752',
            'Interactive Version 63 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-752-v63-compliance-ui.md',
            'completed',
            'Provide a web dashboard at /v63-compliance-hub with EPFME calculators and REST APIs.',
            1, 1, 1, 0,
            'tests/test_v63_features.py'
        ),
        (
            'US-753',
            'End-to-End V63 Verification Test Suite',
            'normal',
            'docs/stories/US-753-v63-test-suite.md',
            'completed',
            'Verify EPFME calculations, salvage rate adjustments, exemptions, and API endpoints.',
            1, 1, 1, 0,
            'tests/test_v63_features.py'
        )
    ]
    
    for s in stories:
        # Delete if exists to avoid primary key conflict on retry
        c.execute("DELETE FROM story WHERE id = ?", (s[0],))
        # Insert
        c.execute(
            """INSERT INTO story 
            (id, title, risk_lane, contract_doc, status, notes, unit_proof, integration_proof, e2e_proof, platform_proof, evidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            s
        )
    
    conn.commit()
    print("Successfully registered V62 & V63 stories in harness.db")
    conn.close()

if __name__ == '__main__':
    main()
