import sqlite3
import os

def register_v41_stories():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    stories = [
        (
            'US-530',
            'Export Customs Declaration XML Parser',
            'normal',
            'planned',
            'docs/stories/US-530-customs-parser.md',
            'Parse XML files simulating GDC export declarations to extract export values, dates, and HS codes.'
        ),
        (
            'US-531',
            'Export Customs-to-Invoice Matcher',
            'normal',
            'planned',
            'docs/stories/US-531-customs-matcher.md',
            'Automatically reconcile customs declarations with GTGT/export invoices, verifying values and currency.'
        ),
        (
            'US-532',
            'Form 01-1/GTGT Export VAT List Builder',
            'normal',
            'planned',
            'docs/stories/US-532-form-01-1-gtgt.md',
            'Build the export goods list Form 01-1/GTGT matching invoices to cleared customs declarations per Circular 80.'
        ),
        (
            'US-533',
            'Form 01/ĐNHT Refund Packet Wizard',
            'normal',
            'planned',
            'docs/stories/US-533-form-01-dnht.md',
            'Wizard to compile Circular 80 tax refund application Form 01/ĐNHT using allocated input VAT.'
        ),
        (
            'US-534',
            'Export VAT Refund Compliance Dashboard & Timeline',
            'normal',
            'planned',
            'docs/stories/US-534-refund-dashboard.md',
            'Dashboard tracking non-cash payment proofs and displaying a premium interactive SVG timeline of refund stages.'
        ),
        (
            'US-535',
            'End-to-End V41 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-535-v41-test-suite.md',
            'Comprehensive testing covering customs parsing, reconciliation matching, Circular 80 form generation, and compliance UI.'
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
    print("V41 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_v41_stories()
