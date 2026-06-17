import sqlite3
import datetime

def main():
    conn = sqlite3.connect("harness.db")
    c = conn.cursor()
    
    stories = [
        # V66 (GHG Emissions & Carbon Credits)
        (
            'US-780',
            'Core GHG Emission & Carbon Credit Compliance Engine',
            'normal',
            'docs/stories/US-780-ghg-calculation.md',
            'planned',
            'Calculate GHG emission loads (CO2, CH4, N2O) and carbon credit offsets under Decree 06/2022/NĐ-CP.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-781',
            'GHG Exemption Auditor and Ozone Mitigation Inspector',
            'normal',
            'docs/stories/US-781-ghg-exemptions.md',
            'planned',
            'Verify carbon exemptions and allocations for registered small emitters under 3,000 tonnes CO2e/year.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-782',
            'Interactive Version 66 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-782-v66-compliance-ui.md',
            'planned',
            'Provide a web dashboard at /v66-compliance-hub with GHG calculations and REST APIs.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-783',
            'End-to-End V66 Verification Test Suite',
            'normal',
            'docs/stories/US-783-v66-test-suite.md',
            'planned',
            'Verify carbon accounting, pollutant GWP scaling factors, exemptions, and API endpoints.',
            0, 0, 0, 0,
            None
        ),
        # V67 (Scrap Import Deposit)
        (
            'US-790',
            'Core Scrap Import Environmental Deposit Engine',
            'normal',
            'docs/stories/US-790-scrap-calculation.md',
            'planned',
            'Calculate import deposit fees for steel, paper, and plastic scrap categories under Decree 08/2022/NĐ-CP.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-791',
            'Scrap Import Exemption & Refund Auditor',
            'normal',
            'docs/stories/US-791-scrap-exemptions.md',
            'planned',
            'Verify deposit refund criteria, recycling quotas, and small importer exemptions under Article 41.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-792',
            'Interactive Version 67 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-792-v67-compliance-ui.md',
            'planned',
            'Provide a web dashboard at /v67-compliance-hub with scrap deposit calculators and REST APIs.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-793',
            'End-to-End V67 Verification Test Suite',
            'normal',
            'docs/stories/US-793-v67-test-suite.md',
            'planned',
            'Verify scrap category rates, refund percentages, import volume validations, and API endpoints.',
            0, 0, 0, 0,
            None
        ),
        # V68 (Biodiversity Offset)
        (
            'US-800',
            'Core Biodiversity Offset & Conservation Fee Engine',
            'normal',
            'docs/stories/US-800-biodiversity-calculation.md',
            'planned',
            'Calculate biodiversity offset fees and ecological restoration charges under the 2008 Law on Biodiversity.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-801',
            'Biodiversity Offset Exemption Inspector',
            'normal',
            'docs/stories/US-801-biodiversity-exemptions.md',
            'planned',
            'Verify conservation fee waivers for small sustainable farming and public national defense projects.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-802',
            'Interactive Version 68 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-802-v68-compliance-ui.md',
            'planned',
            'Provide a web dashboard at /v68-compliance-hub with biodiversity offset calculators and REST APIs.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-803',
            'End-to-End V68 Verification Test Suite',
            'normal',
            'docs/stories/US-803-v68-test-suite.md',
            'planned',
            'Verify ecosystem service calculations, conservation offset rates, exemptions, and API endpoints.',
            0, 0, 0, 0,
            None
        ),
        # V69 (Oil Spill Risk Fee)
        (
            'US-810',
            'Core Oil Spill Response & Risk Fee Engine',
            'normal',
            'docs/stories/US-810-oil-spill-calculation.md',
            'planned',
            'Calculate spill risk management fees and emergency cleaning costs under Decision 12/2021/QĐ-TTg.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-811',
            'Spill Response Exemption & Mitigation Auditor',
            'normal',
            'docs/stories/US-811-oil-spill-exemptions.md',
            'planned',
            'Verify risk fee waivers and reductions for compliant facilities with certified double-hull tankers.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-812',
            'Interactive Version 69 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-812-v69-compliance-ui.md',
            'planned',
            'Provide a web dashboard at /v69-compliance-hub with oil spill calculators and REST APIs.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-813',
            'End-to-End V69 Verification Test Suite',
            'normal',
            'docs/stories/US-813-v69-test-suite.md',
            'planned',
            'Verify risk level coefficients, cleaning costs, exemptions, and API endpoints.',
            0, 0, 0, 0,
            None
        ),
        # V70 (Ozone-Depleting Substances)
        (
            'US-820',
            'Core Ozone-Depleting Substances (ODS) Quota Engine',
            'normal',
            'docs/stories/US-820-ods-calculation.md',
            'planned',
            'Calculate ODS import/export licensing fees and ozone-depleting potential based charges under Decree 06/2022/NĐ-CP.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-821',
            'ODS License Allocation & Exemption Inspector',
            'normal',
            'docs/stories/US-821-ods-exemptions.md',
            'planned',
            'Verify ozone quota exemptions for research, medical uses, and small scale allocations under 50 kg/year.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-822',
            'Interactive Version 70 Compliance Hub UI and API',
            'normal',
            'docs/stories/US-822-v70-compliance-ui.md',
            'planned',
            'Provide a web dashboard at /v70-compliance-hub with ODS calculators and REST APIs.',
            0, 0, 0, 0,
            None
        ),
        (
            'US-823',
            'End-to-End V70 Verification Test Suite',
            'normal',
            'docs/stories/US-823-v70-test-suite.md',
            'planned',
            'Verify ODS classifications (HCFC, HFC, CFC), ODP scaling factors, exemptions, and API endpoints.',
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
    print("Successfully registered V66 to V70 stories in harness.db")
    conn.close()

if __name__ == '__main__':
    main()
