import sqlite3
import os

def register_v40_stories():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    stories = [
        (
            'US-520',
            'FCT (Foreign Contractor Tax) Auditing & Form 01/NTNN Calculation Engine',
            'normal',
            'planned',
            'docs/stories/US-520-fct-withholding.md',
            'Compute withholding tax components (FCT-VAT and FCT-CIT) for foreign vendors under Circular 103/2014/TT-BTC.'
        ),
        (
            'US-521',
            'Related-Party Transaction Detector & Decree 132 EBITDA Cap Auditor',
            'normal',
            'planned',
            'docs/stories/US-521-ebitda-cap.md',
            'Track related parties, compute EBITDA, enforce 30% interest expense cap under Decree 132/2020/NĐ-CP.'
        ),
        (
            'US-522',
            'E-Invoice XML Signature Authenticator & Certificate Chain Validator',
            'normal',
            'planned',
            'docs/stories/US-522-xml-signature.md',
            'Extract X.509 signature metadata from GDT e-invoice XML files and check against trusted Vietnamese CAs.'
        ),
        (
            'US-523',
            'Interactive FCT & Related Party Compliance Dashboard UI',
            'normal',
            'planned',
            'docs/stories/US-523-v40-dashboard.md',
            'Render glassmorphic calculator, related party compliance sandbox, and certificate auditor panel.'
        ),
        (
            'US-524',
            'End-to-End V40 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-524-v40-test-suite.md',
            'Comprehensive testing covering FCT calculations, EBITDA caps, signature metadata checks, and routes.'
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
    print("V40 stories successfully registered/updated in harness.db")

if __name__ == "__main__":
    register_v40_stories()
