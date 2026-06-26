import sqlite3

def register():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO story (
            id, title, risk_lane, status, contract_doc, notes
        ) VALUES (
            'US-CIT-CHATBOT-RAG', 
            'Corporate Income Tax (CIT) 2025/2026 RAG Chatbot Integration', 
            'normal', 
            'in_progress', 
            'docs/stories/US-CIT-CHATBOT-RAG.md', 
            'Deepen chatbot RAG with new CIT regulations (VBHN 61/VBHN-VPQH & TT 20/2026/TT-BTC) and FTS5 search improvements.'
        )
    """)
    conn.commit()
    conn.close()
    print("Story US-CIT-CHATBOT-RAG successfully registered in harness.db")

if __name__ == "__main__":
    register()
