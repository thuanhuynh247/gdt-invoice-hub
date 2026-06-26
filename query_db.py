import sqlite3

conn = sqlite3.connect("harness.db")
c = conn.cursor()
import sqlite3

conn = sqlite3.connect("harness.db")
c = conn.cursor()
c.execute("SELECT id, title, status, notes FROM story")
stories = c.fetchall()
print(f"Total stories: {len(stories)}")
for r in stories:
    if r[2] != 'completed':
        print(f"ID: {r[0]} | Title: {r[1]} | Status: {r[2]}")
        print(f"Notes: {r[3]}")
        print("-" * 40)
conn.close()
