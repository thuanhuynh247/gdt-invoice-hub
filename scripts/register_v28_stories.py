import sqlite3

def register_stories():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()

    stories = [
        {
            "id": "US-396",
            "title": "Collaborative Swarm Chat Advisor & Simulation Panel",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-396-swarm-chat.md",
            "notes": "Generate step-by-step collaborative agent communication logs discussing corporate tax risks and output synthesized audit reports.",
            "evidence": "tests/test_v28_features.py"
        },
        {
            "id": "US-397",
            "title": "Decree 123 XML Compliance Auditing & Auto-Repair Suite",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-397-xml-repair.md",
            "notes": "Audit XML elements, sanitize MSTs, switch payment methods above limit, order tags according to GDT schema, and embed mock HSM signatures.",
            "evidence": "tests/test_v28_features.py"
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
    print("All V28 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
