import sqlite3
import sys

conn = sqlite3.connect('harness.db')
c = conn.cursor()
rows = c.execute("select id, title, status from story").fetchall()
for r in rows:
    print(f"{r[0]}: {r[1]} ({r[2]})")
conn.close()
