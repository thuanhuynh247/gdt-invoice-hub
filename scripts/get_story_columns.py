import sqlite3

conn = sqlite3.connect('harness.db')
cur = conn.cursor()
cur.execute("PRAGMA table_info(story)")
for col in cur.fetchall():
    print(col)
conn.close()
