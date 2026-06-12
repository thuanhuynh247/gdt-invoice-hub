import sqlite3

conn = sqlite3.connect("harness.db")
c = conn.cursor()
c.execute("SELECT id, title, status FROM story ORDER BY id")
for r in c.fetchall():
    print(r)
conn.close()
