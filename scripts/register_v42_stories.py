import sqlite3
import os

def register_v42_stories():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    stories = [
        (
            'US-540',
            'Transfer Pricing Transaction Ingestion & Benchmark Comparator Engine',
            'normal',
            'planned',
            'docs/stories/US-540-transfer-pricing.md',
            'Ingest related-party transactions, compare profit margins against interquartile arm\'s length range, and compute CIT taxable adjustments under Decree 132.'
        ),
        (
            'US-541',
            'Form 01/132 (Related-Party Disclosures & CIT Adjustments) XML Exporter',
            'normal',
            'planned',
            'docs/stories/US-541-form-01-132.md',
            'Generate GDT-compliant Form 01/132 XML file for related-party transaction disclosures and CIT adjustments.'
        ),
        (
            'US-542',
            'E-Commerce Transaction Matcher & Circular 80 Withholding Auditor',
            'normal',
            'planned',
            'docs/stories/US-542-ecommerce-matcher.md',
            'Import Shopee/Lazada/TikTok transaction logs and reconcile them with issued sales invoices under Circular 80.'
        ),
        (
            'US-543',
            'Interactive Transfer Pricing & E-Commerce Audit Dashboard UI',
            'normal',
            'planned',
            'docs/stories/US-543-v42-dashboard.md',
            'Render interactive dashboard at /v42-advanced-audit featuring SVG Arm\'s Length range visualizer, upload widget, and Swarm debate panel.'
        ),
        (
            'US-544',
            'End-to-End V42 Verification Test Suite',
            'normal',
            'planned',
            'docs/stories/US-544-v42-test-suite.md',
            'Comprehensive testing covering transfer pricing adjustments, XML validation of Form 01/132, e-commerce matching, and dashboard routes.'
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
    print("V42 stories successfully registered in harness.db")

if __name__ == "__main__":
    register_v42_stories()
