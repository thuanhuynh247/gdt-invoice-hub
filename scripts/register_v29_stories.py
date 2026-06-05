import sqlite3

def register_stories():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()

    stories = [
        {
            "id": "US-400",
            "title": "Ghost Company Blacklist Scraper & Probability Index Engine",
            "risk_lane": "high_risk",
            "status": "todo",
            "contract_doc": "docs/stories/US-400-ghost-company-detector.md",
            "notes": "Scan seller details against simulated GDT high-risk blacklist and calculate Ghost Company Probability Index based on registry metrics.",
            "evidence": "tests/test_v29_features.py"
        },
        {
            "id": "US-401",
            "title": "Dynamic Audit Defense Letter Builder & Swarm Rectification Panel",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-401-audit-defense-letter.md",
            "notes": "AI-driven template generator and collaborative agent swarm panel for resolving suspect invoice transactions.",
            "evidence": "tests/test_v29_features.py"
        },
        {
            "id": "US-402",
            "title": "SVG Interactive Vietnamese Tax Knowledge Graph & Regulatory Q&A",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-402-tax-knowledge-graph.md",
            "notes": "Stunning SVG interactive node graph visualizing relationships between Decree 123, Circular 80, Circular 219, Decree 125 and Circular 132.",
            "evidence": "tests/test_v29_features.py"
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
    print("All V29 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
