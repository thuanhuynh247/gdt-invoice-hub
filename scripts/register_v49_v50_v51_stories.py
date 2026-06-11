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
        # V49 Stories
        (
            'US-610',
            'Revenue-Scaled CIT Classifier & RE Loss Offset Engine (Law 67, Article 10)',
            'normal',
            'planned',
            'docs/stories/US-610-sme-tax-rates.md',
            'Determine CIT rate based on annual revenue (15% for <3B, 17% for 3B-50B, 20% standard), and calculate RE loss offset.'
        ),
        (
            'US-611',
            'Digital Platform CIT Auditor & Green Exemption Scanner (Law 67, Articles 4 & 8)',
            'normal',
            'planned',
            'docs/stories/US-611-ecommerce-cit.md',
            'Audit digital purchases for foreign providers withholdings and track CIT exemptions for carbon credits/green bonds.'
        ),
        (
            'US-612',
            'Interactive Version 49 Compliance Hub UI and API',
            'normal',
            'planned',
            'docs/stories/US-612-v49-compliance-ui.md',
            'Web dashboard console at /v49-compliance-hub displaying CIT estimators, offset logs, and API routes.'
        ),
        (
            'US-613',
            'End-to-End V49 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-613-v49-test-suite.md',
            'Comprehensive testing covering SME tax brackets, digital platforms CIT withholding, green bonds, and API endpoints.'
        ),
        
        # V50 Stories
        (
            'US-620',
            'Household Business PIT Exemption & Revenue Tracker (Law 109)',
            'normal',
            'planned',
            'docs/stories/US-620-household-pit.md',
            'Audit household business revenue against 500M non-taxable threshold, and determine proper PIT rates (0.5% - 2.0%) for excess.'
        ),
        (
            'US-621',
            'Wage progressive brackets scheduler & Family Deduction Engine (Law 109, Article 7)',
            'normal',
            'planned',
            'docs/stories/US-621-salary-brackets.md',
            'Calculate progressive PIT brackets (5% to 35%) and family deductions (15M personal, 5.5M per dependent) on salaries.'
        ),
        (
            'US-622',
            'Interactive Version 50 Compliance Hub UI and API',
            'normal',
            'planned',
            'docs/stories/US-622-v50-compliance-ui.md',
            'Web dashboard console at /v50-compliance-hub displaying PIT calculations, family deductions, and APIs.'
        ),
        (
            'US-623',
            'End-to-End V50 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-623-v50-test-suite.md',
            'Comprehensive testing covering household PIT, wage tax brackets, family deduction evaluations, and API endpoints.'
        ),
        
        # V51 Stories
        (
            'US-630',
            'E-Transaction Auditing & Digital Signature Integrity Engine (Law 108)',
            'normal',
            'planned',
            'docs/stories/US-630-etransaction-compliance.md',
            'Audit digital signature certificate expirations, verify transmission delays, and log errors.'
        ),
        (
            'US-631',
            'Cross-Border E-Commerce Vendor Tax & Withholding Tracker (Law 108)',
            'normal',
            'planned',
            'docs/stories/US-631-crossborder-ecommerce.md',
            'Sync foreign vendor registrations and calculate digital purchase B2B withholding tax (VAT + CIT).'
        ),
        (
            'US-632',
            'Interactive Version 51 Compliance Hub UI and API',
            'normal',
            'planned',
            'docs/stories/US-632-v51-compliance-ui.md',
            'Web dashboard console at /v51-compliance-hub displaying signature timelines, withholding logs, and APIs.'
        ),
        (
            'US-633',
            'End-to-End V51 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-633-v51-test-suite.md',
            'Comprehensive testing covering digital signature verification, late transmission, e-commerce withholding, and endpoints.'
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
    print("V49, V50, and V51 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
