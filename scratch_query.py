import sqlite3

conn = sqlite3.connect('harness.db')
conn.text_factory = lambda x: x.decode('utf-8', errors='ignore')
cur = conn.cursor()

# Query story table
cur.execute("SELECT id, title, status FROM story ORDER BY id DESC")
stories = cur.fetchall()
print(f"Total Stories: {len(stories)}")
statuses = {}
for s in stories:
    print(s)
    statuses[s[2]] = statuses.get(s[2], 0) + 1
print("Status Counts:", statuses)









