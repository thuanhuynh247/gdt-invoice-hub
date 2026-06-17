import sqlite3

def register_stories():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()

    stories = [
        {
            "id": "US-380",
            "title": "Social Insurance (BHXH/BHYT/BHTN) Reconciliation & Auditing Engine",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-380-social-insurance-reconciler.md",
            "notes": "Calculate statutory social insurance rates (employee 10.5%, employer 21.5%) and audit payroll details for discrepancies",
            "evidence": "tests/test_v26_features.py"
        },
        {
            "id": "US-381",
            "title": "PIT Finalization Settlement & Insurance Reconciliation Dashboard UI",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-381-insurance-reconciliation-ui.md",
            "notes": "Render interactive reconciliation summary tables, audit flags, details panel, and export CSV audit reports",
            "evidence": "tests/test_v26_features.py"
        },
        {
            "id": "US-382",
            "title": "Electronic Tax Ledger (Sổ thuế điện tử) Sync & Reconciliation Engine",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-382-electronic-tax-ledger.md",
            "notes": "Synchronize taxpayer's e-tax balances (CIT, VAT liabilities, penalty interest, overpaid amounts) and match against accounting records",
            "evidence": "tests/test_v26_features.py"
        },
        {
            "id": "US-383",
            "title": "VietQR Dynamic Payment Slip Generator & Interactive Tax Payment Status Panel UI",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-383-vietqr-payment-wizard.md",
            "notes": "Generate Napas 247-compliant VietQR tax payment codes and display realtime simulation status changes in UI panel",
            "evidence": "tests/test_v26_features.py"
        },
        {
            "id": "US-384",
            "title": "Vietnamese Tax Law Knowledge Graph Constructor & Vector Store Indexer",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-384-tax-knowledge-graph.md",
            "notes": "Construct structural knowledge graph links and vector indexes for Decree 123, Circular 80, and Decree 132 for RAG citation queries",
            "evidence": "tests/test_v26_features.py"
        },
        {
            "id": "US-385",
            "title": "Dynamic Audit Defense Document Composer & Socratic Advisory Panel UI",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-385-audit-defense-composer.md",
            "notes": "Create official defense and explanation documents citing specific tax provisions with interactive advisor questionnaire panel",
            "evidence": "tests/test_v26_features.py"
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
    print("All V26 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
