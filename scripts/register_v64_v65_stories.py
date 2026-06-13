import sqlite3
import datetime

def main():
    conn = sqlite3.connect("harness.db")
    c = conn.cursor()
    
    stories = [
        # V64 (Solid Waste)
        (
            'US-760',
            'Core Environment Protection Fee for Solid Waste Engine',
            'normal',
            'docs/stories/US-760-epfsw-calculation.md',
            'planned',
            'Calculate EPFSW for hazardous waste (100,000 VND/tonne) and ordinary waste classes (20,000 to 40,000 VND/tonne) under Decree 164/2016/NĐ-CP.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-761',
            'EPFSW Exemption Auditor',
            'normal',
            'docs/stories/US-761-epfsw-exemptions.md',
            'planned',
            'Verify solid waste fee exemptions for on-site self-recycling/reuse, agricultural composting/livestock feed, and domestic waste from certified rural households.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-762',
            'Interactive Version 64 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-762-v64-compliance-ui.md',
            'planned',
            'Provide a web dashboard at /v64-compliance-hub with EPFSW calculators and REST APIs.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-763',
            'End-to-End V64 Verification Test Suite',
            'normal',
            'docs/stories/US-763-v64-test-suite.md',
            'planned',
            'Verify solid waste calculations, categories, exemptions, history logging, and API endpoints.',
            0, 0, 0, 0,
            None
        ),
        # V65 (EPR)
        (
            'US-770',
            'Core EPR Recycling Fee Engine',
            'normal',
            'docs/stories/US-770-epr-calculation.md',
            'planned',
            'Calculate EPR contributions for batteries, tires, lubricants, and packaging under Decree 08/2022/NĐ-CP using F = R * V * Fs formula.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-771',
            'EPR Compliance Auditor and Exemption Inspector',
            'normal',
            'docs/stories/US-771-epr-exemptions.md',
            'planned',
            'Verify EPR exemptions for export-only goods, revenue under 30 billion VND, imports under 20 billion VND, and closed-loop recycling systems.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-772',
            'Interactive Version 65 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-772-v65-compliance-ui.md',
            'planned',
            'Provide a web dashboard at /v65-compliance-hub with EPR calculators and REST APIs.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-773',
            'End-to-End V65 Verification Test Suite',
            'normal',
            'docs/stories/US-773-v65-test-suite.md',
            'planned',
            'Verify EPR calculations, packaging category coefficients, revenue thresholds, exemptions, and API endpoints.',
            0, 0, 0, 0,
            None
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
    print("Successfully registered V64 & V65 stories in harness.db")
    conn.close()

if __name__ == '__main__':
    main()
