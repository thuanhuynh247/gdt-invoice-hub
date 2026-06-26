import os
import sys
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "invoices.db")

def test():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query 1: test Luật 149
    q1 = "Luật 149"
    cursor.execute("""
        SELECT chunk_content, document_source, page_number
        FROM tax_regulation_fts
        WHERE tax_regulation_fts MATCH ?
        LIMIT 2
    """, (q1,))
    res1 = cursor.fetchall()
    print("=== TEST QUERY: 'Luật 149' ===")
    for row in res1:
        print(f"[{row[1]} - Page {row[2]}]: {row[0][:150]}...")
        
    # Query 2: test Thông tư 20/2026
    q2 = "Thông tư 20"
    cursor.execute("""
        SELECT chunk_content, document_source, page_number
        FROM tax_regulation_fts
        WHERE tax_regulation_fts MATCH ?
        LIMIT 2
    """, (q2,))
    res2 = cursor.fetchall()
    print("\n=== TEST QUERY: 'Thông tư 20' ===")
    for row in res2:
        print(f"[{row[1]} - Page {row[2]}]: {row[0][:150]}...")
        
    conn.close()

if __name__ == "__main__":
    test()
