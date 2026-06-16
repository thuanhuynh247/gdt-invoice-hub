import sqlite3
import datetime

def main():
    conn = sqlite3.connect("harness.db")
    c = conn.cursor()
    
    stories = [
        # V71 (E-Waste & Electronics Disposal EPR Surcharge)
        (
            'US-850',
            'Core E-Waste Recycling & Disposal Fee Engine',
            'normal',
            'docs/stories/US-850-ewaste-calculation.md',
            'planned',
            'Calculate product-specific recycling fees for electronics, batteries, and solar panels under Decree 08/2022/NĐ-CP.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-851',
            'E-Waste Recycling Exemption & Small Importer Auditor',
            'normal',
            'docs/stories/US-851-ewaste-exemptions.md',
            'planned',
            'Verify EPR exemptions for exported electronic goods and small-scale importers with net revenue < 30B VND.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-852',
            'Interactive Version 71 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-852-v71-compliance-ui.md',
            'planned',
            'Provide a web dashboard at /v71-compliance-hub with E-Waste recycling fee calculators and REST APIs.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-853',
            'End-to-End V71 Verification Test Suite',
            'normal',
            'docs/stories/US-853-v71-test-suite.md',
            'planned',
            'Verify electronics recycling fee formulas, small-scale importer thresholds, export exemptions, and API routes.',
            0, 0, 0, 0,
            None
        ),
        # V72 (Industrial Wastewater Treatment Surcharge)
        (
            'US-860',
            'Core Industrial Wastewater Surcharge Engine',
            'normal',
            'docs/stories/US-860-wastewater-calculation.md',
            'planned',
            'Calculate environmental protection fees for industrial wastewater based on COD, TSS, and heavy metals under Decree 53/2020/NĐ-CP.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-861',
            'Wastewater Exemption Auditor',
            'normal',
            'docs/stories/US-861-wastewater-exemptions.md',
            'planned',
            'Verify fee exemptions for cooling water loops, clean water treatment, and municipal sewage fee overlap.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-862',
            'Interactive Version 72 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-862-v72-compliance-ui.md',
            'planned',
            'Provide a web dashboard at /v72-compliance-hub with wastewater calculators and REST APIs.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-863',
            'End-to-End V72 Verification Test Suite',
            'normal',
            'docs/stories/US-863-v72-test-suite.md',
            'planned',
            'Verify pollutant loading calculations, cooling water exemptions, municipal fee deductions, and API endpoints.',
            0, 0, 0, 0,
            None
        ),
        # V73 (Hazardous Waste Management & Disposal Licensing)
        (
            'US-870',
            'Core Hazardous Waste Disposal & Licensing Engine',
            'normal',
            'docs/stories/US-870-hazardous-waste-calculation.md',
            'planned',
            'Calculate hazardous waste licensing fees and volume-based disposal surcharges under Decree 08/2022/NĐ-CP.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-871',
            'Hazardous Waste Exemption & Small Generator Auditor',
            'normal',
            'docs/stories/US-871-hazardous-waste-exemptions.md',
            'planned',
            'Verify licensing exemptions for small-scale generators producing less than 600 kg of hazardous waste per year.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-872',
            'Interactive Version 73 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-872-v73-compliance-ui.md',
            'planned',
            'Provide a web dashboard at /v73-compliance-hub with hazardous waste calculators and REST APIs.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-873',
            'End-to-End V73 Verification Test Suite',
            'normal',
            'docs/stories/US-873-v73-test-suite.md',
            'planned',
            'Verify hazardous waste categories, licensing fees, small generator registration exemptions, and API endpoints.',
            0, 0, 0, 0,
            None
        ),
        # V74 (Noise & Vibration Pollution Surcharge)
        (
            'US-880',
            'Core Noise & Vibration Pollution Surcharge Engine',
            'normal',
            'docs/stories/US-880-noise-calculation.md',
            'planned',
            'Calculate environmental surcharges for noise and vibration levels exceeding QCVN standards under Law on EP 2020.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-881',
            'Noise & Vibration Exemption Auditor',
            'normal',
            'docs/stories/US-881-noise-exemptions.md',
            'planned',
            'Verify exemptions for public construction works, emergency relief sirens, and short-term traditional festivals.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-882',
            'Interactive Version 74 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-882-v74-compliance-ui.md',
            'planned',
            'Provide a web dashboard at /v74-compliance-hub with noise and vibration calculators and REST APIs.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-883',
            'End-to-End V74 Verification Test Suite',
            'normal',
            'docs/stories/US-883-v74-test-suite.md',
            'planned',
            'Verify noise exceedance dB calculations, shift multipliers (day/night), festival/emergency exemptions, and API endpoints.',
            0, 0, 0, 0,
            None
        ),
        # V75 (Single-Use Plastics & Ocean Pollution Levy)
        (
            'US-890',
            'Core Single-Use Plastics & Ocean Pollution Levy Engine',
            'normal',
            'docs/stories/US-890-plastics-calculation.md',
            'planned',
            'Calculate environmental levies on single-use plastic bags, cups, and packaging materials under Decree 08/2022/NĐ-CP.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-891',
            'Biodegradable Plastic Certification & Exemption Inspector',
            'normal',
            'docs/stories/US-891-plastics-exemptions.md',
            'planned',
            'Verify exemptions for certified biodegradable plastics, export packaging, and small agricultural mulching films.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-892',
            'Interactive Version 75 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-892-v75-compliance-ui.md',
            'planned',
            'Provide a web dashboard at /v75-compliance-hub with plastic levy calculators and REST APIs.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-893',
            'End-to-End V75 Verification Test Suite',
            'normal',
            'docs/stories/US-893-v75-test-suite.md',
            'planned',
            'Verify plastic unit/weight rates, biodegradable certification exemptions, export packaging exclusions, and API endpoints.',
            0, 0, 0, 0,
            None
        )
    ]
    
    for s in stories:
        c.execute("DELETE FROM story WHERE id = ?", (s[0],))
        c.execute(
            """INSERT INTO story 
            (id, title, risk_lane, contract_doc, status, notes, unit_proof, integration_proof, e2e_proof, platform_proof, evidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            s
        )
    
    conn.commit()
    print("Successfully registered V71 to V75 stories in harness.db")
    conn.close()

if __name__ == '__main__':
    main()
