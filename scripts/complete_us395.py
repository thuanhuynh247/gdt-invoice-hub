import sqlite3
conn = sqlite3.connect('harness.db')
conn.cursor().execute("UPDATE story SET status = 'completed', evidence = 'tests/test_v27_features.py' WHERE id = 'US-395'")
conn.commit()
conn.close()
print('US-395 updated to completed successfully!')
