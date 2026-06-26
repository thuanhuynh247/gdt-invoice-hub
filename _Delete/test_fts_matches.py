import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "invoices.db")

def test():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    queries = ["Luật 149", "Thông tư 20/2026", "Doanh thu 500 triệu", "Ủy quyền cá nhân"]
    for q in queries:
        print(f"\n--- MATCHING: '{q}' ---")
        import re
        clean_q = re.sub(r'[^\w\s\d]', ' ', q).strip()
        c.execute("""
            SELECT document_source, page_number, chunk_content
            FROM tax_regulation_fts
            WHERE tax_regulation_fts MATCH ?
            LIMIT 3
        """, (clean_q,))
        rows = c.fetchall()
        for r in rows:
            print(f"[{r[0]} P{r[1]}]: {r[2][:150]}...")
            
    conn.close()

if __name__ == "__main__":
    test()
