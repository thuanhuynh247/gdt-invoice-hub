import sqlite3

conn = sqlite3.connect('harness.db')
c = conn.cursor()
rows = c.execute("SELECT id, title, status FROM story WHERE status NOT IN ('completed', 'implemented')").fetchall()
if not rows:
    print("All stories are completed or implemented!")
else:
    print("Pending stories:")
    for r in rows:
        print(f"ID: {r[0]} | Title: {r[1]} | Status: {r[2]}")
conn.close()
