import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "data", "invoices.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

print("--- DISTINCT SOURCES IN TAX_REGULATION_CHUNK ---")
c.execute("SELECT DISTINCT document_source FROM tax_regulation_chunk")
for r in c.fetchall():
    print(r[0])

print("\n--- DISTINCT SOURCES IN TAX_REGULATION_FTS ---")
c.execute("SELECT DISTINCT document_source FROM tax_regulation_fts")
for r in c.fetchall():
    print(r[0])

print("\n--- SAMPLE CHUNK FROM THONGTU69 ---")
c.execute("SELECT chunk_content, page_number FROM tax_regulation_fts WHERE document_source = 'thongtu69_2025.pdf' LIMIT 1")
res = c.fetchone()
if res:
    print(f"Page {res[1]}: {res[0][:200]}...")
else:
    print("No chunks found for thongtu69_2025.pdf")

conn.close()
