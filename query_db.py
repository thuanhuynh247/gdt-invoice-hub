import sqlite3

conn = sqlite3.connect("harness.db")
c = conn.cursor()
c.execute("SELECT id, title, notes FROM story WHERE id IN ('US-910', 'US-920')")
for r in c.fetchall():
    print(f"ID: {r[0]}")
    print(f"Title: {r[1]}")
    print(f"Notes: {r[2]}")
    print("-" * 40)
conn.close()
