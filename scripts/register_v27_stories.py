import sqlite3

def register_stories():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()

    stories = [
        {
            "id": "US-390",
            "title": "Electronic Delivery Notes XML Sync & Validation Parser",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-390-delivery-notes-sync.md",
            "notes": "Synchronize, parse, and validate XML schemas for Electronic Delivery Notes (PXK) under Decree 123.",
            "evidence": "tests/test_v27_features.py"
        },
        {
            "id": "US-391",
            "title": "Delivery-to-Invoice Reconciliation Dashboard UI",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-391-delivery-reconciliation-ui.md",
            "notes": "Build dashboard UI comparing delivery items (SKUs, quantities, prices) against final issued invoices.",
            "evidence": "tests/test_v27_features.py"
        },
        {
            "id": "US-392",
            "title": "Pre-Audit Corporate Tax Risk Scoring Engine",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-392-pre-audit-risk-scorecard.md",
            "notes": "Calculate an overall Tax Risk Index (0-100) based on statutory rules, related-party interest caps, and supplier flags.",
            "evidence": "tests/test_v27_features.py"
        },
        {
            "id": "US-393",
            "title": "Interactive Tax Risk Radar SVG & Audit Advisory Dashboard UI",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-393-risk-radar-dashboard-ui.md",
            "notes": "Render dynamic SVG radar chart of risk domains and interactive panels proposing corrective legal actions.",
            "evidence": "tests/test_v27_features.py"
        },
        {
            "id": "US-394",
            "title": "E-Contract XML Metadata Parser and Milestone Tracker",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-394-econtract-milestone-tracker.md",
            "notes": "Parse structured e-contracts to extract payment terms, values, signatures, and match them against invoices.",
            "evidence": "tests/test_v27_features.py"
        },
        {
            "id": "US-395",
            "title": "Smart Treasury & VAT Forecast Scenario Sandbox UI",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-395-treasury-scenario-sandbox.md",
            "notes": "Slider-based sandbox to model tax liabilities, payments schedule, and daily cash flow requirements.",
            "evidence": "tests/test_v27_features.py"
        }
    ]

    for s in stories:
        cur.execute("""
            INSERT OR REPLACE INTO story (
                id, title, risk_lane, status, contract_doc, notes, evidence,
                unit_proof, integration_proof, e2e_proof, platform_proof
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, 0, 0)
        """, (s["id"], s["title"], s["risk_lane"], s["status"], s["contract_doc"], s["notes"], s["evidence"]))
        print(f"Registered story {s['id']}")

    conn.commit()
    conn.close()
    print("All V27 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
