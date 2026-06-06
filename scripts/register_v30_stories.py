import sqlite3

def register_stories():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()

    stories = [
        {
            "id": "US-410",
            "title": "Transfer Pricing & Arm's Length Transaction Analysis Engine",
            "risk_lane": "high_risk",
            "status": "todo",
            "contract_doc": "docs/stories/US-410-transfer-pricing-engine.md",
            "notes": "Verify profit markup on related-party transactions and audit interquartile range (IQR) compliance under Decree 132/2020/ND-CP.",
            "evidence": "tests/test_v30_features.py"
        },
        {
            "id": "US-411",
            "title": "Interactive SVG Arm's Length Visualizer & Markup Sensitivity Modeler",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-411-markup-visualizer.md",
            "notes": "Build an interactive SVG chart displaying the Arm's Length Range and target company margin with sliders to model markup sensitivity.",
            "evidence": "tests/test_v30_features.py"
        },
        {
            "id": "US-412",
            "title": "AI Tax Audit Prep Advisor & Multi-Agent Swarm Collaboration Hub",
            "risk_lane": "normal",
            "status": "todo",
            "contract_doc": "docs/stories/US-412-audit-prep-advisor.md",
            "notes": "Build a multi-agent consensus swarm chat for audit preparation and generate a print-ready Transfer Pricing Audit Preparation Dossier.",
            "evidence": "tests/test_v30_features.py"
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
    print("All V30 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_stories()
