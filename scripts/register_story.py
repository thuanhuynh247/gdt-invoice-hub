import sqlite3

def register():
    conn = sqlite3.connect("harness.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO story (
            id, title, risk_lane, status, contract_doc, notes
        ) VALUES (
            'US-212', 
            'He thong Canh bao Som NCC Bo tron & Danh gia Tin nhiem AI', 
            'normal', 
            'in_progress', 
            'docs/stories/US-212-supplier-risk-radar.md', 
            'Xay dung he thong quet rui ro nha cung cap, phat hien dau hieu bo tron/ma bang cac thuat toan canh bao som va AI.'
        )
    """)
    conn.commit()
    conn.close()
    print("Story US-212 successfully registered/updated in harness.db")

if __name__ == "__main__":
    register()
