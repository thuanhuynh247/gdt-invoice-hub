import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "..", "data", "invoices.db")
conn = sqlite3.connect(db_path)
c = conn.cursor()

docs = ['thongtu69_2025.pdf', 'thongtu18_2026.pdf', 'nghidinh144_2026.pdf']
for doc in docs:
    print(f"Deleting chunks for {doc}...")
    # Find chunk ids to delete from FTS
    c.execute("SELECT id FROM tax_regulation_chunk WHERE document_source = ?", (doc,))
    chunk_ids = [r[0] for r in c.fetchall()]
    for cid in chunk_ids:
        c.execute("DELETE FROM tax_regulation_fts WHERE chunk_id = ?", (cid,))
    c.execute("DELETE FROM tax_regulation_chunk WHERE document_source = ?", (doc,))

conn.commit()
conn.close()
print("Clean up finished.")
