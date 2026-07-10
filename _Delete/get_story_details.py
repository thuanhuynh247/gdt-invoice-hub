import sqlite3

def main():
    conn = sqlite3.connect('harness.db')
    cur = conn.cursor()
    cur.execute("SELECT id, title, risk_lane, status, notes, evidence FROM story WHERE status != 'completed'")
    for row in cur.fetchall():
        print(f"ID: {row[0]}")
        print(f"Title: {row[1]}")
        print(f"Risk Lane: {row[2]}")
        print(f"Status: {row[3]}")
        print(f"Notes: {row[4]}")
        print(f"Evidence: {row[5]}")
        print("-" * 50)
    conn.close()

if __name__ == "__main__":
    main()
