import sqlite3
from datetime import datetime

def register_stories():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()

    stories = [
        # Version 20.0.0 Stories
        {
            "id": "US-320",
            "title": "Local Agent Mailroom & Coordination Hub",
            "risk_lane": "normal",
            "status": "implemented",
            "contract_doc": "docs/stories/US-320-local-agent-mailroom.md",
            "notes": "Implement structured JSON-based message coordination and locking for local specialist agents.",
            "evidence": "tests/test_ai_swarm.py"
        },
        {
            "id": "US-321",
            "title": "Autonomous Joint Audit Coordinator",
            "risk_lane": "normal",
            "status": "implemented",
            "contract_doc": "docs/stories/US-321-joint-audit-coordinator.md",
            "notes": "Parse complex prompts, delegate sub-tasks to specialists, and compile unified report.",
            "evidence": "tests/test_ai_swarm.py"
        },
        {
            "id": "US-322",
            "title": "Bank Feed Ingestion & Transaction Normalizer",
            "risk_lane": "normal",
            "status": "implemented",
            "contract_doc": "docs/stories/US-322-bank-feed-ingestion.md",
            "notes": "Parse ISO 20022 Bank XML/CSV transaction statements into standard database model.",
            "evidence": "tests/test_bank_matching.py"
        },
        {
            "id": "US-323",
            "title": "Automated Bank-to-Invoice Matcher",
            "risk_lane": "normal",
            "status": "implemented",
            "contract_doc": "docs/stories/US-323-bank-to-invoice-matcher.md",
            "notes": "Pair bank statement payments with corresponding purchase/sales invoices with risk warnings.",
            "evidence": "tests/test_bank_matching.py"
        },
        {
            "id": "US-324",
            "title": "Machine Learning Tax Liability Predictor",
            "risk_lane": "normal",
            "status": "implemented",
            "contract_doc": "docs/stories/US-324-ml-tax-liability-predictor.md",
            "notes": "Forecast VAT and CIT liabilities 12 months ahead with confidence intervals.",
            "evidence": "tests/test_predictive_forecasting.py"
        },
        {
            "id": "US-325",
            "title": "Tax Scenario Simulation Sandbox",
            "risk_lane": "normal",
            "status": "implemented",
            "contract_doc": "docs/stories/US-325-tax-scenario-sandbox.md",
            "notes": "Sandbox interface for financial planning to simulate tax holidays and M&A pricing.",
            "evidence": "tests/test_predictive_forecasting.py"
        },
        # Version 21.0.0 Stories
        {
            "id": "US-330",
            "title": "Taxpayer Network Graph Generator",
            "risk_lane": "normal",
            "status": "implemented",
            "contract_doc": "docs/stories/US-330-network-graph-generator.md",
            "notes": "Construct transaction graph nodes and edges representation from local historical invoices.",
            "evidence": "tests/test_graph_fraud.py"
        },
        {
            "id": "US-331",
            "title": "VAT Fraud Ring Network Detector",
            "risk_lane": "normal",
            "status": "implemented",
            "contract_doc": "docs/stories/US-331-vat-fraud-ring-detector.md",
            "notes": "Run Graph cycles & PageRank outlier filters to detect suspicious transaction loops.",
            "evidence": "tests/test_graph_fraud.py"
        },
        {
            "id": "US-332",
            "title": "Immutable Cryptographic Merkle Ledger",
            "risk_lane": "normal",
            "status": "implemented",
            "contract_doc": "docs/stories/US-332-immutable-merkle-ledger.md",
            "notes": "Hash invoices sequentially, saving proof receipts into local secure store.",
            "evidence": "tests/test_cryptographic_ledger.py"
        },
        {
            "id": "US-333",
            "title": "Zero-Knowledge Proof Tax Compliance",
            "risk_lane": "normal",
            "status": "implemented",
            "contract_doc": "docs/stories/US-333-zkp-compliance-verifier.md",
            "notes": "Build proof protocols validating total invoice VAT matches rates without value disclosure.",
            "evidence": "tests/test_cryptographic_ledger.py"
        },
        {
            "id": "US-334",
            "title": "Customs XML Declaration Parser",
            "risk_lane": "normal",
            "status": "implemented",
            "contract_doc": "docs/stories/US-334-customs-xml-parser.md",
            "notes": "Parse Customs import declarations, extracting duties, VAT base, and exchange rates.",
            "evidence": "tests/test_customs_reconciler.py"
        },
        {
            "id": "US-335",
            "title": "Import VAT Reconciliation & Mitigation",
            "risk_lane": "normal",
            "status": "implemented",
            "contract_doc": "docs/stories/US-335-import-vat-reconciliation.md",
            "notes": "Match customs records with actual XML invoices to automatically draft tax declarations.",
            "evidence": "tests/test_customs_reconciler.py"
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
    print("All V20 and V21 stories successfully registered/marked as implemented in harness.db")

if __name__ == "__main__":
    register_stories()
