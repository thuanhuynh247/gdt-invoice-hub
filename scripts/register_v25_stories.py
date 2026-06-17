import sqlite3

def register_stories():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()

    stories = [
        {
            "id": "US-370",
            "title": "GDT Portal Syncing & Status Verification Crawler/Agent",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-370-gdt-portal-sync.md",
            "notes": "Verify transmission statuses on GDT gateway and assign approved verification codes",
            "evidence": "tests/test_v25_portal_sync.py"
        },
        {
            "id": "US-371",
            "title": "Invoice Verification Status Dashboard UI",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-371-verification-status-ui.md",
            "notes": "Display GDT verification statuses, codes, error logs, and trigger manual re-syncs",
            "evidence": "tests/test_v25_portal_sync.py"
        },
        {
            "id": "US-372",
            "title": "E-Invoice Correction & Replacement XML Generator",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-372-correction-replacement-xml.md",
            "notes": "Generate Decree 123 conforming XMLs for corrected and replaced invoices referencing original GDT codes",
            "evidence": "tests/test_v25_corrections.py"
        },
        {
            "id": "US-373",
            "title": "Form 04/SS-HĐĐT XML Generator & GDT Transmission Wizard",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-373-form-04-ss-wizard.md",
            "notes": "Scaffold, sign, and transmit Form 04/SS-HĐĐT XML packages reporting invoice errors to GDT",
            "evidence": "tests/test_v25_corrections.py"
        },
        {
            "id": "US-374",
            "title": "Corporate Tax Optimization & Scenario Modeler Engine",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-374-tax-optimization-engine.md",
            "notes": "Analyze CIT/VAT liabilities under custom tax holiday schedules, deductible limits, and pricing markup options",
            "evidence": "tests/test_v25_optimization.py"
        },
        {
            "id": "US-375",
            "title": "Tax Scenario Sandbox & Optimization Advisory Panel UI",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-375-tax-sandbox-ui.md",
            "notes": "Interactive dashboard sandbox with parameter sliders, comparison charts, and PDF export reports",
            "evidence": "tests/test_v25_optimization.py"
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
    print("All V25 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
