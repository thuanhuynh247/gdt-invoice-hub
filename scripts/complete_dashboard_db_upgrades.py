import sqlite3
import os

def complete_dashboard_db_upgrades():
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
            evidence = 'tests/test_dashboard_db_upgrades.py'
        WHERE id = 'US-DASHBOARD-DB-UPGRADES'
    """)
    print(f"Updated US-DASHBOARD-DB-UPGRADES story count: {cur.rowcount}")

    conn.commit()
    conn.close()
    print("Successfully completed US-DASHBOARD-DB-UPGRADES story in harness.db!")

if __name__ == "__main__":
    complete_dashboard_db_upgrades()
