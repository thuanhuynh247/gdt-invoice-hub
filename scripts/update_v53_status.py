import sqlite3

conn = sqlite3.connect("harness.db")
cur = conn.cursor()
for sid in ["US-650", "US-651", "US-652", "US-653"]:
    cur.execute("UPDATE story SET status='completed' WHERE id=?", (sid,))
conn.commit()
print(f"Updated {cur.rowcount} stories to completed")
conn.close()
