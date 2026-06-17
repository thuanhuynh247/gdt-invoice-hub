import sqlite3

def register_stories():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()

    stories = [
        {
            "id": "US-340",
            "title": "Statutory Tax Penalty & Interest Calculator",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-340-tax-penalty-calculator.md",
            "notes": "Automatically compute tax penalties (Decree 125/2020/NĐ-CP) and daily late interest (0.03%) on tax variances",
            "evidence": "tests/test_v22_tax_audit.py"
        },
        {
            "id": "US-341",
            "title": "AI-Generated Audit Explanation & Defense Template Builder",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-341-audit-explanation-builder.md",
            "notes": "Generate official Vietnamese explanation letters responding to specific audit risks",
            "evidence": "tests/test_v22_tax_audit.py"
        },
        {
            "id": "US-342",
            "title": "Shopee, Lazada & TikTok Shop Order Normalizer",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-342-ecommerce-order-normalizer.md",
            "notes": "Parse CSV/JSON export feeds from e-commerce platforms into standardized orders",
            "evidence": "tests/test_v22_ecommerce.py"
        },
        {
            "id": "US-343",
            "title": "E-Commerce Tax Compliance Matching & Warning Engine",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-343-ecommerce-compliance-matching.md",
            "notes": "Pair platform transactions against issued e-invoices, detecting tax declaration gaps",
            "evidence": "tests/test_v22_ecommerce.py"
        },
        {
            "id": "US-344",
            "title": "Interactive Payroll Audit Dashboard",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-344-payroll-audit-dashboard.md",
            "notes": "Audit employees' progressive PIT rates and statutory insurance withholdings in a web view",
            "evidence": "tests/test_v22_payroll_pit.py"
        },
        {
            "id": "US-345",
            "title": "PIT Finalizer & Form 05/QTT-TNCN UI",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-345-pit-xml-exporter-ui.md",
            "notes": "Step-by-step wizard to finalize PIT, previewing and exporting GDT-compliant XML",
            "evidence": "tests/test_v22_payroll_pit.py"
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
    print("All V22 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
