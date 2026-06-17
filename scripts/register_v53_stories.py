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
        # V53 Stories
        (
            'US-650',
            'Core EP Tax Calculation Engine',
            'normal',
            'planned',
            'docs/stories/US-650-ep-tax-calculation.md',
            'Classify and calculate EP tax on fuels, coal, plastic bags, and chemicals using absolute tax-per-unit formulas.'
        ),
        (
            'US-651',
            'EP Tax Exemption & Green Transition Auditor',
            'normal',
            'planned',
            'docs/stories/US-651-ep-tax-exemptions.md',
            'Audit exemptions for biodegradable plastics, coal for domestic electricity generation, and re-export exclusions.'
        ),
        (
            'US-652',
            'Interactive Version 53 Compliance Hub UI and API',
            'normal',
            'planned',
            'docs/stories/US-652-v53-compliance-ui.md',
            'Provide a web dashboard at /v53-compliance-hub containing EP tax calculators, logs, and REST JSON APIs.'
        ),
        (
            'US-653',
            'End-to-End V53 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-653-v53-test-suite.md',
            'Verify EP tax rates, biodegradable certifications, coal exemptions, dashboard routes, and database logs.'
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
    print("V53 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
