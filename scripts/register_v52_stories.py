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
        # V52 Stories
        (
            'US-640',
            'Sugary Beverages Roadmap & Air Conditioner Classifier Engine (Law 66)',
            'normal',
            'planned',
            'docs/stories/US-640-sct-beverages-ac.md',
            'Classify and calculate SCT on sugary drinks (>5g/100ml) using 2026-2028 roadmap and audit AC capacities (24k to 90k BTU taxable at 10%).'
        ),
        (
            'US-641',
            'Inland to Non-Tariff Area SCT Auditor & Promotion Price Calculator (Law 66)',
            'normal',
            'planned',
            'docs/stories/US-641-nontariff-promo-sct.md',
            'Audit inland sales into non-tariff zones (excluding cars <24 seats) and compute promotion SCT base prices using equivalent market values.'
        ),
        (
            'US-642',
            'Interactive Version 52 Compliance Hub UI and API',
            'normal',
            'planned',
            'docs/stories/US-642-v52-compliance-ui.md',
            'Web dashboard console at /v52-compliance-hub displaying SCT calculations, promotional adjusters, and APIs.'
        ),
        (
            'US-643',
            'End-to-End V52 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-643-v52-test-suite.md',
            'Comprehensive testing covering sugary beverage rates, AC thresholds, non-tariff exclusions, promotion calculations, and APIs.'
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
    print("V52 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
