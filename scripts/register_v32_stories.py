import sqlite3

def register():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()
    
    stories = [
        (
            'US-430',
            'Interactive Exporter VAT Refund Wizard with Glassmorphism Progress Metrics',
            'normal',
            'in_progress',
            'docs/stories/US-430-refund-wizard.md',
            'Render a multi-step wizard dashboard for profiling, auditing purchases, customs reconciliation, and viewing refund metrics.'
        ),
        (
            'US-431',
            'Form 01/DNHT Refund Request Packet Builder & GDT XML Exporter',
            'normal',
            'in_progress',
            'docs/stories/US-431-refund-builder.md',
            'Construct GDT-compliant Form 01/DNHT XML containing profiles, bank details, purchase invoices, and reconciled customs records.'
        ),
        (
            'US-432',
            'AI Swarm VAT Refund Justification Compiler & Multi-Agent Legal Defense Panel',
            'normal',
            'in_progress',
            'docs/stories/US-432-refund-swarm.md',
            'Simulate three-agent swarm (Auditor, Customs Liaison, Counsel) debating the refund pack and drafting a legal defense letter.'
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
    print("V32 stories successfully registered/updated in harness.db")

if __name__ == "__main__":
    register()
