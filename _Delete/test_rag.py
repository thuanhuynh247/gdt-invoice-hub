import sqlite3

def run():
    conn = sqlite3.connect('data/invoices.db')
    c = conn.cursor()
    query = "giao dịch liên kết EBITDA 30"
    
    # Try match
    try:
        c.execute("""
            SELECT document_source, page_number, chunk_content, bm25(tax_regulation_fts) 
            FROM tax_regulation_fts 
            WHERE tax_regulation_fts MATCH ? 
            ORDER BY bm25(tax_regulation_fts) ASC
        """, (query,))
        res = c.fetchall()
        print("MATCH results:")
        for r in res:
            print(r[0], r[1], r[3], r[2][:60])
    except Exception as e:
        print("MATCH failed:", e)

    # Try OR match
    try:
        words = query.split()
        fts_query = " OR ".join(words)
        c.execute("""
            SELECT document_source, page_number, chunk_content, bm25(tax_regulation_fts) 
            FROM tax_regulation_fts 
            WHERE tax_regulation_fts MATCH ? 
            ORDER BY bm25(tax_regulation_fts) ASC
        """, (fts_query,))
        res = c.fetchall()
        print("\nOR MATCH results:")
        for r in res:
            print(r[0], r[1], r[3], r[2][:60])
    except Exception as e:
        print("OR MATCH failed:", e)

if __name__ == "__main__":
    run()
