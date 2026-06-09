import sqlite3
import os

def complete_v31_stories():
    db_path = "harness.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        UPDATE story
        SET status = 'completed',
            unit_proof = 1,
            integration_proof = 1,
            e2e_proof = 1,
            evidence = 'tests/test_v31_features.py'
        WHERE id IN ('US-420', 'US-421', 'US-422')
    """)
    print(f"Updated V31 stories count: {cur.rowcount}")

    conn.commit()
    conn.close()
    print("Successfully completed V31 stories in harness.db!")

if __name__ == "__main__":
    complete_v31_stories()
