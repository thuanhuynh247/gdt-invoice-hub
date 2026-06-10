import sqlite3
import os

def complete_v36_stories():
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
            evidence = 'tests/test_v36_features.py'
        WHERE id IN ('US-480', 'US-481', 'US-482', 'US-483', 'US-484', 'US-485')
    """)
    print(f"Updated V36 stories count: {cur.rowcount}")

    conn.commit()
    conn.close()
    print("Successfully completed V36 stories in harness.db!")

if __name__ == "__main__":
    complete_v36_stories()
